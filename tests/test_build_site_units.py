"""Unit tests for the pure functions in scripts/build_site.py (Markdown subset, diagrams, footnotes, links)."""
import os
import re
import sys
import unittest
import xml.dom.minidom

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "scripts"))
import build_site as bs  # noqa: E402


def ctx(repos=None, pages=None):
    return bs.Ctx(repos or {"pub": "public", "priv": "private"}, pages or {"other.md": "other.html"})


class Slug(unittest.TestCase):
    def test_strips_tags_punctuation_and_case(self):
        self.assertEqual(bs.slug_id("My <code>Role</code>: Here & Now!"), "my-role-here-now")

    def test_collapses_dashes_and_falls_back(self):
        self.assertEqual(bs.slug_id("a  --  b"), "a-b")
        self.assertEqual(bs.slug_id("???"), "section")


class Footnotes(unittest.TestCase):
    def test_numbers_by_first_reference_and_suffixes_repeats(self):
        c = ctx()
        first = c.footnote("b")
        second = c.footnote("a")
        again = c.footnote("b")
        self.assertIn('id="ref-b"', first)
        self.assertIn(">[1]<", first)
        self.assertIn(">[2]<", second)
        self.assertIn('id="ref-b-2"', again)
        self.assertIn(">[1]<", again)
        self.assertEqual(c.order, ["b", "a"])


class Links(unittest.TestCase):
    def test_private_repo_link_gets_a_badge_and_public_does_not(self):
        priv = bs.link_html("x", "https://github.com/AlexRosen23/priv/pull/3", ctx())
        pub = bs.link_html("x", "https://github.com/AlexRosen23/pub/pull/3", ctx())
        self.assertIn('class="gh private"', priv)
        self.assertIn('class="badge"', priv)
        self.assertNotIn("badge", pub)

    def test_unknown_repo_is_not_badged_private(self):
        self.assertNotIn("badge", bs.link_html("x", "https://github.com/AlexRosen23/ghost", ctx()))

    def test_external_link_keeps_href_and_noreferrer(self):
        out = bs.link_html("t", "https://example.com/a?b=1&c=2", ctx())
        self.assertIn('href="https://example.com/a?b=1&amp;c=2"', out)
        self.assertIn('rel="noreferrer"', out)

    def test_md_links_are_mapped_to_html_pages_with_fragment(self):
        self.assertEqual(bs.link_html("t", "../case-studies/other.md#sec", ctx()), '<a href="other.html#sec">t</a>')
        self.assertEqual(bs.link_html("t", "#local", ctx()), '<a href="#local">t</a>')


class Inline(unittest.TestCase):
    def test_escapes_html(self):
        self.assertEqual(bs.inline("<script>alert(1)</script>", ctx()), "&lt;script&gt;alert(1)&lt;/script&gt;")

    def test_code_span_is_protected_from_emphasis_and_links(self):
        out = bs.inline("`**not bold** [a](b)` and **bold**", ctx())
        self.assertIn("<code>**not bold** [a](b)</code>", out)
        self.assertIn("<strong>bold</strong>", out)

    def test_code_span_content_is_escaped(self):
        self.assertIn("<code>&lt;b&gt;</code>", bs.inline("`<b>`", ctx()))

    def test_emphasis_not_applied_to_math_stars(self):
        self.assertNotIn("<em>", bs.inline("2 * 3 * 4", ctx()))
        self.assertIn("<em>x</em>", bs.inline("an *x* here", ctx()))

    def test_br_tags_survive_but_other_tags_do_not(self):
        out = bs.inline("a<br/>b<i>c</i>", ctx())
        self.assertIn("a<br>b", out)
        self.assertNotIn("<i>", out)

    def test_footnote_reference_and_link_render_together(self):
        c = ctx()
        out = bs.inline("claim[^s1] see [doc](https://example.com)", c)
        self.assertIn('href="#src-s1"', out)
        self.assertIn('<a href="https://example.com" rel="noreferrer">doc</a>', out)
        self.assertEqual(c.order, ["s1"])

    def test_link_text_with_injection_attempt_stays_escaped(self):
        out = bs.inline('[<img src=x onerror=1>](https://example.com)', ctx())
        self.assertNotIn("<img", out)


class Flowchart(unittest.TestCase):
    def test_parse_nodes_labels_and_edges(self):
        d, order, labels, edges = bs.parse_flowchart(
            ['flowchart TD', 'A["Start"] --> B(Mid)', 'B -->|yes| C{End}'])
        self.assertEqual(d, "TD")
        self.assertEqual(order, ["A", "B", "C"])
        self.assertEqual(labels, {"A": "Start", "B": "Mid", "C": "End"})
        self.assertEqual(edges, [("A", "B", ""), ("B", "C", "yes")])

    def test_ampersand_fans_out_and_comments_are_skipped(self):
        _d, order, _l, edges = bs.parse_flowchart(
            ["graph LR", "%% a comment", "subgraph s", "A --> B & C", "end", "classDef x fill:#fff"])
        self.assertEqual(order, ["A", "B", "C"])
        self.assertEqual(edges, [("A", "B", ""), ("A", "C", "")])

    def test_direction_defaults_to_lr_and_tb_becomes_td(self):
        self.assertEqual(bs.parse_flowchart(["flowchart LR", "A --> B"])[0], "LR")
        self.assertEqual(bs.parse_flowchart(["graph BT", "A --> B"])[0], "TD")
        self.assertEqual(bs.parse_flowchart(["weird", "A --> B"])[0], "LR")

    def test_layout_assigns_layers_along_edges(self):
        layer, cols = bs.layout(["A", "B", "C", "D"], [("A", "B", ""), ("B", "C", ""), ("A", "D", "")])
        self.assertEqual(layer, {"A": 0, "B": 1, "C": 2, "D": 1})
        self.assertEqual(cols[1], ["B", "D"])

    def test_layout_terminates_on_a_cycle(self):
        layer, _cols = bs.layout(["A", "B"], [("A", "B", ""), ("B", "A", "")])
        self.assertTrue(all(v < 2 for v in layer.values()))

    def test_svg_is_well_formed_and_escapes_labels(self):
        svg, alt = bs.flowchart_svg('flowchart LR\nA["a<br/>b + c"] --> B["<x>"]', "T <1> & co")
        xml.dom.minidom.parseString(svg)  # raises if malformed
        self.assertEqual(svg.count('class="node"'), 2)
        self.assertEqual(svg.count('class="edge"'), 1)
        self.assertIn("T &lt;1&gt; &amp; co", svg)  # the title is escaped too
        self.assertNotIn("<x>", svg)
        self.assertIn("a b + c → &lt;x&gt;", alt)

    def test_long_chain_switches_to_top_down(self):
        src = "flowchart LR\n" + "\n".join(f"N{i} --> N{i + 1}" for i in range(6))
        svg, _alt = bs.flowchart_svg(src, "chain")
        w, h = (int(re.search(rf'{k}="(\d+)"', svg).group(1)) for k in ("width", "height"))
        self.assertGreater(h, w)

    def test_empty_diagram_falls_back_to_code_block(self):
        self.assertEqual(bs.flowchart_svg("flowchart LR", "t"), "")
        self.assertTrue(bs.diagram("flowchart LR", "t").startswith("<pre><code>"))


class Sequence(unittest.TestCase):
    SRC = ("sequenceDiagram\nparticipant U as User (human)\nparticipant S as Server\n"
           "U->>S: ask\nS-->>U: answer\nalt it fails\nS->>U: error\nend")

    def test_messages_are_numbered_in_order_with_reply_arrow(self):
        out = bs.sequence_html(self.SRC)
        self.assertEqual(len(re.findall(r'<li value="', out)), 3)
        self.assertIn('<li value="1"><span class="who">User</span> <span aria-hidden="true">→</span>', out)
        self.assertIn('<li value="2"><span class="who">Server</span> <span aria-hidden="true">⇠</span>', out)
        self.assertIn('<li class="branch">If it fails</li>', out)

    def test_participant_parenthetical_is_dropped_but_unknown_ids_kept(self):
        out = bs.sequence_html("sequenceDiagram\nparticipant U as User (human)\nU->>X: hi")
        self.assertIn(">User<", out)
        self.assertIn(">X<", out)
        self.assertNotIn("(human)", out)

    def test_diagram_dispatch_on_first_line(self):
        self.assertIn("(sequence, in order)", bs.diagram(self.SRC, "T"))
        self.assertIn("<svg", bs.diagram("flowchart LR\nA --> B", "T"))


class Render(unittest.TestCase):
    def render(self, md, c=None):
        return bs.render(md, c or ctx(), "Page")

    def test_headings_get_unique_ids_and_h2_feeds_toc(self):
        body, toc, _ = self.render("## Same\n\ntext\n\n## Same\n\n### Sub\n")
        self.assertEqual([t[0] for t in toc], ["same", "same-2"])
        self.assertIn('<h3 id="sub">', body)

    def test_meta_comment_is_removed(self):
        body, _t, _d = self.render('<!-- meta: {"nav": "x"} -->\n# T\n')
        self.assertNotIn("meta", body)

    def test_paragraph_lines_are_joined(self):
        body, _t, _d = self.render("one\ntwo\n\nthree")
        self.assertEqual(body.count("<p>"), 2)
        self.assertIn("<p>one two</p>", body)

    def test_fenced_code_is_escaped_and_not_interpreted(self):
        body, _t, _d = self.render("```\n# not a heading <b>\n```\n")
        self.assertIn("<pre><code># not a heading &lt;b&gt;</code></pre>", body)
        self.assertNotIn("<h1", body)

    def test_mermaid_fence_becomes_a_titled_figure(self):
        body, _t, _d = self.render("## Architecture\n```mermaid\nflowchart LR\nA --> B\n```\n")
        self.assertIn("Diagram: Architecture", body)
        self.assertIn("<svg", body)

    def test_table_rendering(self):
        body, _t, _d = self.render("| A | B |\n|---|---|\n| 1 | **2** |\n")
        self.assertIn('<th scope="col">A</th>', body)
        self.assertIn("<td><strong>2</strong></td>", body)

    def test_pipe_line_without_separator_is_a_paragraph(self):
        body, _t, _d = self.render("| not | a table |\n")
        self.assertNotIn("<table", body)

    def test_blockquote_lines_merge(self):
        body, _t, _d = self.render("> a\n> b\n")
        self.assertIn("<blockquote><p>a b</p></blockquote>", body)

    def test_footnote_definitions_are_collected_with_continuation_lines(self):
        body, _t, defs = self.render("Text[^a]\n\n[^a]: first\n    second\n")
        self.assertEqual(defs, {"a": "first second"})
        self.assertIn("\x01DEF:a\x01", body)

    def test_nested_and_ordered_lists(self):
        body, _t, _d = self.render("- a\n  - b\n- c\n\n1. x\n2. y\n")
        self.assertIn("<ul><li>a<ul><li>b</li></ul></li><li>c</li></ul>", body)
        self.assertIn("<ol><li>x</li><li>y</li></ol>", body)


class Sources(unittest.TestCase):
    def test_numbered_by_reference_order_then_unreferenced_then_missing(self):
        c = ctx()
        c.footnote("b")
        c.footnote("a")
        out = bs.sources_html({"a": "A text", "b": "B text", "z": "Unused"}, c)
        ids = re.findall(r'<li id="src-(\w+)"', out)
        self.assertEqual(ids, ["b", "a", "z"])
        self.assertEqual(out.count("class=\"back\""), 2)  # the unreferenced one has no back-link

    def test_missing_definition_is_flagged(self):
        c = ctx()
        c.footnote("ghost")
        self.assertIn("(missing source)", bs.sources_html({}, c))


class ListHtml(unittest.TestCase):
    def test_dedent_closes_nested_lists(self):
        out = bs.list_html([[0, False, "a"], [2, False, "b"], [4, True, "c"], [0, False, "d"]], ctx())
        self.assertEqual(out, "<ul><li>a<ul><li>b<ol><li>c</li></ol></li></ul></li><li>d</li></ul>")


class Page(unittest.TestCase):
    def test_current_nav_link_is_marked_and_titles_escaped(self):
        out = bs.page("T <x>", "<p>b</p>", [("One", "one.html"), ("Two & Co", "two.html")], "desc", current="two.html")
        self.assertEqual(out.count('aria-current="page"'), 1)
        self.assertIn('href="two.html" aria-current="page">Two &amp; Co<', out)
        self.assertIn("T &lt;x&gt;", out)
        self.assertTrue(out.startswith("<!doctype html>"))


if __name__ == "__main__":
    unittest.main()
