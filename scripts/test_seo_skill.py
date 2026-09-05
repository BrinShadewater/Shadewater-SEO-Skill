from __future__ import annotations

import json
import tempfile
import urllib.error
import unittest
from pathlib import Path
from unittest import mock

import fetch_page
import broken_links
import entity_checker
import generate_report
import pagespeed

import console_safe  # noqa: F401  (side effect: UTF-8 stdout/stderr)


class SeoSkillTests(unittest.TestCase):
    def test_entity_score_weights_info_less_than_warning(self) -> None:
        data = {
            "sections": {
                "security": {},
                "social": {},
                "robots": {},
                "broken_links": {},
                "internal_links": {},
                "redirects": {},
                "llms_txt": {},
                "pagespeed": {"performance_score": 85},
                "onpage": {"title": "Example", "meta_description": "Desc", "h1": ["H1"], "canonical": "https://example.com"},
                "readability": {"flesch_reading_ease": 65},
                "entity": {
                    "sameas_analysis": {"total_found": 5},
                    "wikidata": {"found": False},
                    "wikipedia": {"found": False},
                    "issues": [
                        {"severity": "Warning"},
                        {"severity": "Warning"},
                        {"severity": "Info"},
                        {"severity": "Info"},
                    ],
                },
                "link_profile": {},
                "hreflang": {},
                "duplicate_content": {},
            }
        }

        scores = generate_report.calculate_overall_score(data)

        self.assertEqual(scores["categories"]["entity"], 57)

    def test_entity_checker_falls_back_to_get_for_social_sameas(self) -> None:
        head_error = urllib.error.HTTPError(
            url="https://www.twitch.tv/brinshadewater",
            code=405,
            msg="Method Not Allowed",
            hdrs=None,
            fp=None,
        )

        class FakeResponse:
            def __init__(self, status: int):
                self.status = status

            def __enter__(self):
                return self

            def __exit__(self, exc_type, exc, tb):
                return False

        def fake_urlopen(request, timeout=6):
            method = request.get_method()
            if method == "HEAD":
                raise head_error
            return FakeResponse(200)

        with mock.patch.object(entity_checker, "validate_public_url", return_value="https://www.twitch.tv/brinshadewater"), \
             mock.patch.object(entity_checker.urllib.request, "urlopen", side_effect=fake_urlopen):
            result = entity_checker.analyze_sameas(["https://www.twitch.tv/brinshadewater"])

        self.assertEqual(result["issues"], [])

    def test_pagespeed_parses_successful_api_response(self) -> None:
        fake_response = mock.Mock()
        fake_response.status_code = 200
        fake_response.json.return_value = {
            "lighthouseResult": {
                "categories": {"performance": {"score": 0.91}},
                "audits": {
                    "largest-contentful-paint": {"numericValue": 2400},
                    "first-contentful-paint": {"numericValue": 1500},
                    "server-response-time": {"numericValue": 500},
                    "render-blocking-resources": {
                        "score": 0.4,
                        "title": "Eliminate render-blocking resources",
                        "displayValue": "Potential savings of 320 ms",
                        "details": {"type": "opportunity", "overallSavingsMs": 320},
                        "description": "Remove render blocking resources.",
                    },
                },
            },
            "loadingExperience": {
                "metrics": {
                    "LARGEST_CONTENTFUL_PAINT_MS": {
                        "percentile": 2300,
                        "category": "FAST",
                    }
                }
            },
        }

        with mock.patch.object(pagespeed.requests, "get", return_value=fake_response):
            result = pagespeed.get_pagespeed("https://example.com", api_key="psi-test-key")

        self.assertEqual(result["performance_score"], 91)
        self.assertTrue(result["field_data_available"])
        self.assertEqual(result["metrics"]["LCP"]["value"], 2300)
        self.assertEqual(result["opportunities"][0]["savings_ms"], 320)

    def test_pagespeed_api_key_resolution_supports_env_var(self) -> None:
        with mock.patch.dict(
            "os.environ",
            {"PAGESPEED_API_KEY": "psi-test-key"},
            clear=False,
        ):
            self.assertEqual(generate_report.resolve_pagespeed_api_key(), "psi-test-key")
            self.assertEqual(pagespeed.resolve_api_key(), "psi-test-key")

    def test_pagespeed_api_key_resolution_prefers_domain_specific_env_var(self) -> None:
        with mock.patch.dict(
            "os.environ",
            {
                "PAGESPEED_API_KEY": "global-key",
                "PAGESPEED_API_KEY_SHADEWATERLABS_COM": "domain-key",
            },
            clear=True,
        ):
            self.assertEqual(
                generate_report.resolve_pagespeed_api_key("https://shadewaterlabs.com"),
                "domain-key",
            )
            self.assertEqual(
                generate_report.resolve_pagespeed_api_key("https://other.example"),
                "global-key",
            )

    def test_classic_theme_escapes_site_derived_strings(self) -> None:
        payload = '<img src=x onerror=alert(1)>'
        href = '"><script>1</script>'
        data = {
            "domain": "example.com",
            "url": "https://example.com",
            "timestamp": "2026-03-15T12:00:00",
            "sections": {
                "social": {"og_tags": {"og:title": payload}, "twitter_tags": {}},
                "security": {"headers_present": {}, "headers_missing": {"X-Frame-Options": payload}},
                "broken_links": {"broken": [{"url": href, "is_internal": True, "status": payload, "anchor_text": payload}]},
                "internal_links": {"anchor_texts": {payload: 3}, "orphan_candidates": [{"url": href, "incoming_links": 0}]},
                "redirects": {"chain": [{"step": 1, "status": 301, "url": href, "time_ms": 1, "redirect_type": payload}]},
            },
            "environment": {"detected": payload},
            "environment_fixes": [],
        }
        scores = {"overall": 50, "categories": {}, "weights": {}}

        html = generate_report.generate_html(data, scores, theme_name="classic")

        self.assertNotIn(payload, html)
        self.assertNotIn("<script>1</script>", html)
        self.assertIn("&lt;img src=x onerror=alert(1)&gt;", html)

    def test_decode_body_caps_a_gzip_bomb(self) -> None:
        import gzip as _gzip
        from net_utils import MAX_DECOMPRESSED_BYTES, decode_body

        bomb = _gzip.compress(b"0" * (MAX_DECOMPRESSED_BYTES + 1_000_000))
        text = decode_body(bomb, {"Content-Encoding": "gzip", "Content-Type": "text/html; charset=utf-8"})
        self.assertLessEqual(len(text), MAX_DECOMPRESSED_BYTES)

    def test_urllib_redirects_to_private_targets_are_blocked(self) -> None:
        import urllib.error
        from net_utils import TrackingRedirectHandler

        handler = TrackingRedirectHandler(max_redirects=5)
        with self.assertRaises(urllib.error.HTTPError):
            handler.redirect_request(None, None, 302, "Found", {}, "http://127.0.0.1/admin")

    def test_generate_html_defaults_to_shadewater_theme(self) -> None:
        data = {
            "domain": "example.com",
            "url": "https://example.com",
            "timestamp": "2026-03-15T12:00:00",
            "sections": {
                "pagespeed": {"error": "Rate limited by Google API"},
                "readability": {"flesch_reading_ease": 37.1, "avg_sentence_length": 16.5},
            },
            "environment": {"detected": "Next.js"},
            "environment_fixes": [{"severity": "Info", "title": "Performance measurement incomplete", "fix": "Rerun with API key."}],
        }
        scores = {
            "overall": 72,
            "categories": {"pagespeed": 0, "readability": 61},
            "weights": {},
        }

        html = generate_report.generate_html(data, scores)

        self.assertIn("SHADEWATER LABS", html)
        self.assertIn("Shadewater SEO Report", html)
        self.assertIn("SEO Audit Suite", html)
        self.assertIn("⬇️ Download PDF", html)
        self.assertIn("📋 Copy Report", html)
        self.assertIn("🤖 Claude Handoff", html)
        self.assertIn("⚙️ Codex Handoff", html)
        self.assertIn("--accent:#234a7c", html)
        self.assertNotIn("#d7b16f", html)
        self.assertIn("sw-tabs", html)
        self.assertIn("data-tab=\"findings\"", html)
        self.assertIn("sw-filter-bar", html)
        self.assertIn("sw-finding-search", html)
        self.assertIn("🔎 Expand Evidence", html)
        self.assertIn("data-count=\"4\"", html)
        self.assertIn("data-severity-filter=\"warning\"", html)
        self.assertIn("filterFindings", html)
        self.assertIn("searchFindings", html)
        self.assertIn("toggleEvidence", html)
        self.assertIn("data-severity=\"info\"", html)
        self.assertIn('<span class="sw-next-emoji">🎯</span>', html)
        self.assertIn('<span class="sw-next-copy">Recommended Next Move</span>', html)
        self.assertIn("📊 Summary", html)
        self.assertIn("🔎 Findings", html)
        self.assertIn("📈 Scores", html)
        self.assertIn("✅ Actions", html)
        self.assertIn("📁 Artifacts", html)
        self.assertIn("🧪 Methodology", html)
        self.assertNotIn("01 📊 Summary", html)
        self.assertNotIn("02 🔎 Findings", html)
        self.assertNotIn("03 📈 Scores", html)
        self.assertNotIn("04 ✅ Actions", html)
        self.assertNotIn("05 📁 Artifacts", html)
        self.assertNotIn("06 🧪 Methodology", html)
        self.assertIn("🚦 Critical Issues", html)
        self.assertIn("⚠️ Warnings", html)
        self.assertIn("💡 Info / Opportunities", html)
        self.assertIn("🌊 Strong Scores", html)
        self.assertIn("sw-url-pill", html)
        self.assertIn("How to read this report", html)
        self.assertIn("Fix sequence", html)
        self.assertIn("sw-summary-groups", html)
        self.assertIn("sw-summary-group critical", html)
        self.assertIn("sw-summary-group warning", html)
        self.assertIn("sw-summary-group info", html)
        self.assertIn("sw-summary-group strong", html)
        self.assertIn("Impact:", html)
        self.assertIn("Effort:", html)
        self.assertIn("Environment / tool limitations", html)
        self.assertIn("🔍 Search findings, evidence, fixes", html)
        self.assertIn("sw-next-move", html)
        self.assertIn("sw-action-card", html)
        self.assertIn("copyAction", html)
        self.assertIn("copyReport", html)
        self.assertIn("copyText", html)
        self.assertIn("REPORT_TEXT", html)
        self.assertIn("CLAUDE_HANDOFF_TEXT", html)
        self.assertIn("CODEX_HANDOFF_TEXT", html)
        self.assertIn("copyClaudeHandoff", html)
        self.assertIn("copyCodexHandoff", html)
        self.assertIn("data-task-text=", html)
        self.assertIn("AUDITOR_SUMMARY", html)
        self.assertIn("The audit found", html)
        self.assertIn("prepareForPrint", html)
        self.assertIn("restoreAfterPrint", html)
        self.assertIn("detailsOpenedForPrint", html)
        self.assertIn("details[open] > summary", html)
        self.assertIn("window.addEventListener('beforeprint'", html)
        self.assertIn("data-finding-id=\"F-02\"", html)
        self.assertIn("N/A<span>/100</span>", html)
        self.assertIn("Provider Scope", html)
        self.assertIn("Action Type", html)
        self.assertIn("Evidence Source", html)
        self.assertIn("Environment-limited", html)
        self.assertIn("PageSpeed", html)
        self.assertIn("sw-score-stack", html)
        self.assertIn("Overall Score", html)
        self.assertIn("Full audit score across technical SEO, content, AI readiness, and site health.", html)
        self.assertIn("Speed Insights", html)
        self.assertIn("Google PageSpeed mobile performance score for Core Web Vitals context.", html)
        self.assertIn("N/A</div><div class=\"sw-score-label\">PAGESPEED", html)
        self.assertIn("CLAUDE-HANDOFF.md", html)
        self.assertIn("CODEX-HANDOFF.md", html)
        self.assertNotIn("unpkg.com/react", html)
        self.assertNotIn("babel.min.js", html)

    def test_generate_html_renders_brand_logo_when_provided(self) -> None:
        data = {
            "domain": "example.com",
            "url": "https://example.com",
            "timestamp": "2026-03-15T12:00:00",
            "sections": {},
            "environment": {},
            "environment_fixes": [],
        }
        scores = {
            "overall": 72,
            "categories": {},
            "weights": {},
        }

        html = generate_report.generate_html(
            data,
            scores,
            brand_logo_uri="data:image/png;base64,abc123",
        )

        self.assertIn("sw-report-logo", html)
        self.assertIn("sw-report-logo-wrap", html)
        self.assertIn("sw-report-head-logo", html)
        self.assertIn("data:image/png;base64,abc123", html)
        self.assertIn("grid-template-columns:minmax(0,1fr) minmax(520px,620px) 220px", html)
        self.assertIn("height:345px", html)
        self.assertIn("margin-bottom:-34px", html)
        self.assertIn("object-position:center bottom", html)
        self.assertIn("sw-score-stack", html)
        self.assertIn(">Overall Score</div><div class=\"sw-score-big\"", html)
        self.assertIn(">Speed Insights</div><div class=\"sw-score-big", html)
        self.assertNotIn(".sw-report-head-logo { min-height:142px; border:", html)
        title_idx = html.index('class="sw-h1"')
        logo_idx = html.index('<div class="sw-report-logo-wrap sw-report-head-logo">')
        score_idx = html.index('class="sw-score-stack"')
        self.assertLess(title_idx, logo_idx)
        self.assertLess(logo_idx, score_idx)

    def test_generate_html_uses_primary_environment_and_speed_indicator(self) -> None:
        data = {
            "domain": "example.com",
            "url": "https://example.com",
            "timestamp": "2026-03-15T12:00:00",
            "sections": {"pagespeed": {"performance_score": 88}},
            "environment": {"primary": "Static / Custom", "runtime": "Static HTML or unknown framework"},
            "environment_fixes": [],
        }
        scores = {
            "overall": 82,
            "categories": {"pagespeed": 88},
            "weights": {},
        }

        html = generate_report.generate_html(data, scores)

        self.assertIn("<dt>Environment</dt><dd>Static / Custom</dd>", html)
        self.assertIn(">Speed Insights</div><div class=\"sw-score-big small\">88</div>", html)
        self.assertIn("PAGESPEED · Good", html)

    def test_detect_environment_falls_back_to_static_custom(self) -> None:
        env = generate_report.detect_environment("<html><body>Hello</body></html>", "https://example.com")

        self.assertEqual(env["primary"], "Static / Custom")
        self.assertEqual(env["runtime"], "Static HTML or unknown framework")
        self.assertEqual(env["confidence"], "low")

    def test_generate_html_tolerates_none_canonical(self) -> None:
        data = {
            "domain": "example.com",
            "url": "https://example.com",
            "timestamp": "2026-03-15T12:00:00",
            "sections": {
                "onpage": {
                    "canonical": None,
                    "title": "Example Title",
                    "meta_description": "Example description",
                    "h1": ["Example H1"],
                }
            },
            "environment": {},
            "environment_fixes": [],
        }
        scores = {
            "overall": 72,
            "categories": {"onpage": 90},
            "weights": {},
        }

        html = generate_report.generate_html(data, scores)

        self.assertIn("Canonical tag is missing", html)
        self.assertIn("No canonical URL was detected", html)

    def test_fetch_page_uses_shared_fetch_helper(self) -> None:
        expected = {
            "url": "https://example.com",
            "status_code": 200,
            "content": "<html></html>",
            "headers": {"Content-Type": "text/html"},
            "redirect_chain": [],
            "error": None,
        }
        with mock.patch.object(fetch_page, "fetch_public_url", return_value=expected) as mocked:
            result = fetch_page.fetch_page("https://example.com", timeout=12, follow_redirects=False, max_redirects=2)

        self.assertEqual(result, expected)
        mocked.assert_called_once_with(
            "https://example.com",
            timeout=12,
            follow_redirects=False,
            max_redirects=2,
        )

    def test_broken_links_refuse_a_redirect_to_a_private_target(self) -> None:
        """A public link that 302s to 127.0.0.1 is reported blocked, never fetched."""
        hop = mock.Mock(status_code=302, headers={"Location": "http://127.0.0.1/admin"})
        with mock.patch.object(broken_links.requests, "request", return_value=hop) as request:
            result = broken_links.check_link({"url": "https://example.com/go"})
        self.assertEqual(result["error"], "blocked_private_target")
        self.assertEqual(request.call_count, 1, "the private hop must not be requested")

    def test_broken_links_record_public_redirect_hops(self) -> None:
        hop = mock.Mock(status_code=301, headers={"Location": "https://example.com/new"})
        final = mock.Mock(status_code=200, headers={}, url="https://example.com/new")
        final.elapsed.total_seconds.return_value = 0.05
        with mock.patch.object(broken_links.requests, "request", side_effect=[hop, final]) as request:
            result = broken_links.check_link({"url": "https://example.com/old"})
        self.assertEqual(result["status"], 200)
        self.assertEqual(result["redirect"]["hops"], 1)
        self.assertEqual(result["redirect"]["codes"], [301])
        self.assertEqual(result["redirect"]["to"], "https://example.com/new")
        for call in request.call_args_list:
            self.assertFalse(call.kwargs["allow_redirects"], "requests must never follow on its own")

    def test_broken_links_treats_external_403_as_blocked(self) -> None:
        page_response = mock.Mock(status_code=200, text='<a href="https://x.com/brinshadewater">X</a>')
        blocked_link = {
            "url": "https://x.com/brinshadewater",
            "anchor_text": "X",
            "is_internal": False,
            "status": 403,
            "error": None,
            "redirect": None,
            "response_time_ms": 120,
        }

        with mock.patch.object(broken_links, "validate_public_url", return_value="https://example.com"), \
             mock.patch.object(broken_links.requests, "get", return_value=page_response), \
             mock.patch.object(broken_links, "check_link", return_value=blocked_link):
            result = broken_links.check_broken_links("https://example.com", max_workers=1)

        self.assertEqual(result["summary"]["broken"], 0)
        self.assertEqual(result["summary"]["blocked"], 1)
        self.assertEqual(len(result["blocked"]), 1)

    def test_maybe_emit_image_handoff_generates_ready_artifact(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            public_dir = root / "public"
            public_dir.mkdir(parents=True, exist_ok=True)
            (public_dir / "hero.jpg").write_bytes(b"fake-jpg")
            html_path = root / "page.html"
            html_path.write_text("<html><head><title>Home</title></head><body></body></html>", encoding="utf-8")
            output_path = root / "seo-image-handoff.json"

            data = {
                "url": "https://example.com/",
                "sections": {
                    "onpage": {
                        "title": "Home",
                        "images": [
                            {
                                "src": "/hero.jpg",
                                "alt": None,
                                "width": "1600",
                                "height": "900",
                                "loading": "eager",
                                "fetchpriority": "high",
                                "srcset": None,
                                "sizes": None,
                                "decoding": None,
                                "role": None,
                                "aria_hidden": None,
                            }
                        ],
                    }
                },
            }

            artifact = generate_report.maybe_emit_image_handoff(
                data,
                html_path=str(html_path),
                public_root=public_dir,
                output_path=output_path,
            )

            self.assertTrue(artifact["generated"])
            self.assertTrue(output_path.exists())
            handoff = json.loads(output_path.read_text(encoding="utf-8"))
            self.assertEqual(handoff["summary"]["ready_count"], 1)
            self.assertEqual(handoff["items"][0]["status"], "ready")

    def test_write_markdown_artifacts_includes_verified_findings_and_handoff(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            html_path = root / "SEO-REPORT.html"
            audit_path = root / "FULL-AUDIT-REPORT.md"
            action_path = root / "ACTION-PLAN.md"
            claude_path = root / "CLAUDE-HANDOFF.md"
            codex_path = root / "CODEX-HANDOFF.md"
            image_handoff_path = root / "seo-image-handoff.json"

            data = {
                "url": "https://example.com/",
                "timestamp": "2026-03-15T12:00:00",
                "environment": {"primary": "Next.js"},
                "environment_fixes": [
                    {
                        "severity": "warning",
                        "title": "Metadata needs work",
                        "fix": "Use the Metadata API for title and OG tags.",
                    }
                ],
                "artifacts": {
                    "image_handoff": {
                        "generated": True,
                        "path": str(image_handoff_path),
                    }
                },
                "sections": {
                    "onpage": {
                        "title": "",
                        "meta_description": "",
                        "h1": [],
                        "canonical": "",
                        "images": [
                            {
                                "src": "/hero.jpg",
                                "alt": None,
                                "width": None,
                                "height": None,
                                "loading": None,
                                "fetchpriority": None,
                                "srcset": None,
                                "sizes": None,
                                "decoding": None,
                                "role": None,
                                "aria_hidden": None,
                            }
                        ],
                    },
                    "security": {"headers_missing": {"Strict-Transport-Security": True}},
                    "social": {"og_missing": ["og:title"], "twitter_missing": []},
                    "llms_txt": {"exists": False},
                    "broken_links": {"summary": {"broken": 2}},
                    "internal_links": {"orphan_candidates": ["/orphan"]},
                    "redirects": {"issues": ["redirect chain"]},
                    "pagespeed": {"performance_score": 42},
                    "readability": {"flesch_reading_ease": 32, "avg_sentence_length": 28},
                    "entity": {"issues": ["missing sameAs"]},
                    "link_profile": {"orphan_pages": {"count": 1}, "dead_end_pages": {"count": 0}},
                    "hreflang": {"summary": {"critical": 0, "high": 1}},
                    "duplicate_content": {"near_duplicates": ["/copy"], "thin_pages": []},
                },
            }
            scores = {
                "overall": 48,
                "categories": {"onpage": 35, "pagespeed": 42, "security": 60},
            }

            findings_bundle = generate_report.build_report_findings(data)
            artifact_paths = generate_report.write_markdown_artifacts(
                data=data,
                scores=scores,
                findings_bundle=findings_bundle,
                audit_report_path=audit_path,
                action_plan_path=action_path,
                claude_handoff_path=claude_path,
                codex_handoff_path=codex_path,
                html_report_path=html_path,
            )

            self.assertTrue(audit_path.exists())
            self.assertTrue(action_path.exists())
            self.assertTrue(claude_path.exists())
            self.assertTrue(codex_path.exists())
            audit_markdown = audit_path.read_text(encoding="utf-8")
            action_markdown = action_path.read_text(encoding="utf-8")
            claude_markdown = claude_path.read_text(encoding="utf-8")
            codex_markdown = codex_path.read_text(encoding="utf-8")
            self.assertIn("# FULL-AUDIT-REPORT", audit_markdown)
            self.assertIn("Primary H1 is missing", audit_markdown)
            self.assertIn("Image handoff", audit_markdown)
            self.assertIn("# ACTION-PLAN", action_markdown)
            self.assertIn("## Critical", action_markdown)
            self.assertIn("seo-handoff", action_markdown)
            self.assertIn("# CLAUDE-HANDOFF", claude_markdown)
            self.assertIn("Claude Code", claude_markdown)
            self.assertIn("do not read secrets", claude_markdown.lower())
            self.assertIn("# CODEX-HANDOFF", codex_markdown)
            self.assertIn("AGENTS.md", codex_markdown)
            self.assertIn("do not reset", codex_markdown.lower())
            self.assertIn("Image handoff", artifact_paths)
            self.assertIn("Claude handoff", artifact_paths)
            self.assertIn("Codex handoff", artifact_paths)

    def test_project_handoff_docs_exist_for_agent_portability(self) -> None:
        project_root = Path(__file__).resolve().parents[1]
        claude_doc = project_root / "CLAUDE.md"
        handoff_doc = project_root / "HANDOFF.md"
        claude_settings = project_root / ".claude" / "settings.json"

        agents_doc = project_root / "AGENTS.md"

        self.assertTrue(claude_doc.exists())
        self.assertTrue(agents_doc.exists())
        self.assertTrue(handoff_doc.exists())
        self.assertTrue(claude_settings.exists())
        # Since 2026-08-06 CLAUDE.md is a Claude Code import stub ("@AGENTS.md") and
        # AGENTS.md is the canonical guide. What must hold is that the content Claude
        # Code loads names the tool: either the stub says so itself, or it imports the
        # file that does.
        claude_text = claude_doc.read_text(encoding="utf-8")
        agents_text = agents_doc.read_text(encoding="utf-8")
        self.assertIn("Shadewater SEO", agents_text)
        self.assertTrue(
            "Shadewater SEO" in claude_text or "@AGENTS.md" in claude_text,
            "CLAUDE.md neither names the tool nor imports AGENTS.md",
        )
        self.assertIn("test_seo_skill", handoff_doc.read_text(encoding="utf-8"))
        self.assertIn(".env", claude_settings.read_text(encoding="utf-8"))

    def test_collect_data_passes_pagespeed_api_key_to_script(self) -> None:
        recorded_calls: list[tuple[str, list[str]]] = []

        def fake_run_script(script_name: str, args: list[str], timeout: int = 120) -> dict:
            recorded_calls.append((script_name, list(args)))
            return {}

        with mock.patch.dict("os.environ", {"PAGESPEED_API_KEY": "psi-test-key"}, clear=False), \
             mock.patch.object(generate_report, "fetch_page", return_value=""), \
             mock.patch.object(generate_report, "run_script", side_effect=fake_run_script), \
             mock.patch.object(generate_report, "detect_environment", return_value={}):
            data = generate_report.collect_data("https://example.com", emit_image_handoff=False)

        self.assertIn("pagespeed", data["sections"])
        pagespeed_calls = [args for name, args in recorded_calls if name == "pagespeed.py"]
        self.assertEqual(len(pagespeed_calls), 1)
        self.assertEqual(
            pagespeed_calls[0],
            ["https://example.com", "--strategy", "mobile", "--api-key", "psi-test-key"],
        )


if __name__ == "__main__":
    unittest.main()
