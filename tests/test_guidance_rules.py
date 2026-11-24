"""The rules that only a skill text or a guidance file carries.

No program enforces these rules: an agent follows the text. The specification names the text as the
proof (docs/spec/SDD.md, "Verified by"), so each test reads the text for the exact rule. A test
fails when an edit removes or changes the rule.
"""
import json
from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[1]


def read(rel):
    return (ROOT / rel).read_text()


def flat(text):
    """The text with each run of white space as one space, so a rule can break over lines."""
    return ' '.join(text.split())


class WritingAndBranchRules(unittest.TestCase):
    """SDD-SC-14, SDD-SC-16 and SDD-SC-17 (TDD-5.20)."""

    def test_each_agent_writes_commit_pr_and_issue_text_in_ste(self):
        rule = 'Write commit, PR and issue text in ASD-STE100. Keep the `type(scope): summary` form.'
        for rel in ('skills/develop/SKILL.md', 'integrations/openrig/agents/worker/guidance/role.md',
                    'integrations/openrig/agents/control/guidance/role.md'):
            with self.subTest(file=rel):
                self.assertIn(rule, read(rel))
        self.assertIn('Write review text in ASD-STE100.', read('integrations/openrig/agents/overseer/guidance/role.md'))

    def test_the_brief_of_a_loop_worker_gives_the_ste_rule(self):
        brief = read('skills/loop/scripts/loop.sh').split('cat > "$wt/.worker-brief.md" <<EOF', 1)[1].split('\nEOF\n', 1)[0]
        self.assertIn('Write commit, PR and issue text in ASD-STE100', brief)
        self.assertIn('Keep the \\`type(scope): summary\\` form.', brief)

    def test_a_desktop_session_works_on_a_wip_branch(self):
        self.assertIn('A desktop session uses a `wip/*` branch. Never push it. Rename it to `type/slug` before a push.',
                      read('skills/develop/SKILL.md'))

    def test_the_zed_built_in_agent_has_the_read_settings(self):
        doc = read('docs/zed.md')
        section = doc.split('## The Zed built-in agent reads only', 1)[1].split('\n## ', 1)[0]
        self.assertIn('Do not use it to write.', section)
        self.assertIn('Do not select the `write` profile. Do not approve an edit from the built-in agent.', section)
        settings = json.loads(re.search(r'```json\n(.*?)\n```', section, re.S).group(1))['agent']
        self.assertEqual(settings['default_profile'], 'ask')
        self.assertIs(settings['always_allow_tool_actions'], False)
        self.assertEqual(settings['tool_permissions']['default'], 'confirm')
        steps = doc.split('\n## Check\n', 1)[1]
        self.assertIn('Confirm that it cannot edit a file without a prompt.', steps)


class DistillSkill(unittest.TestCase):
    """SDD-SC-10, SDD-LP-54 to SDD-LP-57 (TDD-6.10)."""

    def setUp(self):
        self.skill = flat(read('skills/distill/SKILL.md'))
        self.template = read('skills/distill/incoming.template.html')

    def test_the_candidates_go_to_an_incoming_file_that_git_does_not_track(self):
        self.assertIn('`incoming=state` (the default): `~/.local/state/dev-platform/incoming/<repo-name>.html`', self.skill)
        self.assertIn('Git must never track the file', self.skill)
        self.assertIn('git -C <checkout> ls-files --error-unmatch docs/incoming.html` first. If git tracks the file, '
                      'stop and tell the owner.', self.skill)
        self.assertIn('git -C <checkout> check-ignore -q docs/incoming.html', self.skill)
        self.assertIn('Do not change the `.gitignore` of the repository', self.skill)
        self.assertIn('With `incoming=state`, never write the file inside the repository.', self.skill)

    def test_each_candidate_is_ranked_for_congruency_and_complexity(self):
        self.assertIn('Congruency: `already satisfied`, `clarifies`, `amends`, `contradicts`, `brand new` or '
                      '`nonsense`. Cite the specification item ids it touches', self.skill)
        self.assertIn('Complexity: `S`, `M`, `L` or `XL`', self.skill)
        self.assertIn('One line of rationale', self.skill)
        self.assertIn('With `decisions=none` or `decisions=frozen`, an old decision is history: rank against the '
                      'current specification text.', self.skill)
        for congruency in ('satisfied', 'clarifies', 'amends', 'contradicts', 'new', 'nonsense'):
            with self.subTest(congruency=congruency):
                self.assertRegex(self.template, rf'<li class="{congruency}"')
        self.assertIn('<span class="label">Complexity:</span> <span class="badge">', self.template)

    def test_each_candidate_has_an_identifier_of_its_date_and_a_number_of_that_day(self):
        self.assertIn('Candidate ids are `C-YYYY-MM-DD-n`; n starts at 1 and continues within the day across batches',
                      self.skill)
        ids = re.findall(r'<article class="candidate [a-z]+" id="([^"]+)"', self.template)
        self.assertTrue(ids)
        for candidate in ids:
            self.assertRegex(candidate, r'^C-\d{4}-\d\d-\d\d-[1-9]\d*$')

    def test_the_skill_changes_no_tracked_file_issue_or_specification(self):
        self.assertIn('The skill files no issue, edits no specification and opens nothing.', self.skill)
        self.assertIn('never rewrite, reorder or delete an existing block', self.skill)
        self.assertIn('Do not file issues, edit the specification or open anything.', self.skill)
        self.assertIn('<!-- batches below, newest first -->', self.template)

    def test_a_candidate_holds_no_raw_quote_and_no_private_name(self):
        self.assertIn('No raw quotes and no names of private individuals.', self.skill)
        self.assertIn('a source reference by date and type only', self.skill)
        self.assertIn('no quotes, no private names', flat(read('skills/intake/SKILL.md')))


class IntakeSkill(unittest.TestCase):
    """SDD-SC-20, SDD-SC-21, SDD-LP-58, SDD-LP-59 and SDD-LP-61 (TDD-6.11)."""

    def setUp(self):
        self.text = read('skills/intake/SKILL.md')
        self.skill = flat(self.text)

    def section(self, title):
        return flat(self.text.split(f'\n## {title}', 1)[1].split('\n## ', 1)[0])

    def test_a_frozen_repository_gets_no_specification_change(self):
        frozen = self.section('Frozen repository (`decisions=frozen`)')
        self.assertIn('Intake changes no specification here (SDD-SC-20).', frozen)
        self.assertIn('Never edit a specification file', frozen)
        self.assertIn('**Stop** when the source asks for a change of a requirement.', frozen)
        self.assertIn('run `distill`', frozen)
        self.assertIn('the `dev-spec` write commands', frozen)

    def test_a_promoted_or_rejected_candidate_leaves_the_incoming_file(self):
        self.assertIn('When the owner took a candidate in or rejected it, remove its block from `incoming_file` '
                      '(SDD-SC-21) and add its ID to the commit message of the tasks.', self.section('Frozen repository (`decisions=frozen`)'))
        self.assertIn('When a candidate is promoted or rejected, remove its block from `incoming_file` (SDD-SC-21). '
                      'Write its id (`C-YYYY-MM-DD-n`) in the commit message of the specification change.',
                      self.section('Procedure'))

    def test_with_decisions_none_the_specification_changes_after_the_owner_accepts(self):
        procedure = self.section('Procedure')
        self.assertIn('This is the procedure for `decisions=none`, the default.', procedure)
        self.assertIn('Ask in the conversation, and show the exact sentence that changes. Write no file for the '
                      'question. Stop here until the owner answers.', procedure)
        self.assertIn('**Specification change**, after acceptance, as the first commit on the goal\'s branch.', procedure)
        self.assertIn('The commit message gives the reason of the change, the date of the owner\'s acceptance and '
                      'the ID of each candidate.', procedure)

    def test_with_decisions_open_the_decision_is_accepted_first(self):
        open_mode = self.section('Repository with decision records (`decisions=open`)')
        self.assertIn('write each question as a decision draft also', open_mode)
        self.assertIn('`Status: proposed`', open_mode)
        self.assertIn('After the owner accepts, record `Status: accepted` and the date.', open_mode)
        self.assertIn('commit the decisions with the spec and the tasks', open_mode)

    def test_each_task_cites_the_specification_items_that_govern_it(self):
        self.assertIn('Every task cites the specification', self.skill)
        procedure = self.section('Procedure')
        self.assertIn('the SDD/TDD items that govern it', procedure)
        self.assertIn('add `refs` to the SDD/TDD items', procedure)
        self.assertIn('Each task cites current IDs in `refs`.', self.section('Frozen repository (`decisions=frozen`)'))


if __name__ == '__main__':
    unittest.main()
