"""Tests for the four hook scripts: a happy path and a missing-manifesto-file case each."""

import json
import os
import shutil
import subprocess
import tempfile
import sys
import unittest

PLUGIN_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HOOKS = os.path.join(PLUGIN_ROOT, "hooks")
sys.path.insert(0, os.path.join(PLUGIN_ROOT, "unharness", "src", "unharness"))
from config import subagent_key

FIRST_PRINCIPLES = os.path.join(PLUGIN_ROOT, "manifestos", "first-principles.md")


def tagline_of(path):
    with open(path) as f:
        for line in f:
            if line.startswith("tagline:"):
                return line.split(":", 1)[1].strip().strip("\"'")
    raise AssertionError("no tagline in " + path)


def run_hook(script, config, stdin="", plugin_root=PLUGIN_ROOT, files=None, setup_dirs=(), hooks=HOOKS, **extra_env):
    """Run one hook in a fresh project folder, with no config file when config is None; the folder's path rides on the result as `project`."""
    with tempfile.TemporaryDirectory() as project:
        if config is not None:
            os.mkdir(os.path.join(project, ".manifestos"))
            with open(os.path.join(project, ".manifestos", "config.yaml"), "w") as f:
                f.write(config)
        for folder in setup_dirs:
            os.makedirs(os.path.join(project, folder))
        for name, text in (files or {}).items():
            with open(os.path.join(project, name), "w") as f:
                f.write(text)
        env = {k: v for k, v in os.environ.items() if k != "UNHARNESS"}
        env.update(CLAUDE_PLUGIN_ROOT=plugin_root, CLAUDE_PROJECT_DIR=project, **extra_env)
        result = subprocess.run(
            ["bash", os.path.join(hooks, script)],
            input=stdin, capture_output=True, text=True, env=env, timeout=30,
        )
        result.project = project
        return result


def unbound_line(message):
    return f"No manifesto bound: {message}; run unharness doctor for the fix."


def bound_line(script, stdout):
    """Return the context line a binding hook printed: stdout as is for session-start, the additionalContext of its JSON otherwise."""
    if script == "session-start.sh":
        return stdout.rstrip("\n")
    return json.loads(stdout)["hookSpecificOutput"]["additionalContext"].rstrip("\n")


HAPPY = "you:\n  - first-principles\n"
MISSING = "you:\n  - no-such-manifesto\n"
ALL_HOOKS = ("session-start.sh", "post-compact.sh", "subagent-start.sh", "drift-reminder.sh")
BINDING_HOOKS = ("session-start.sh", "post-compact.sh", "subagent-start.sh")
SUBAGENTS = "subagents:\n  other:\n    - {name}\n"
MAIN_SESSION_HOOKS = ("session-start.sh", "post-compact.sh", "drift-reminder.sh")
SUBAGENT_BINDING_CASES = (
    ("a matched key", "subagents:\n  worker:\n    - first-principles\n  other:\n    - no-such-manifesto\n"),
    ("a fall to other", SUBAGENTS.format(name="first-principles")),
    ("no subagents section", HAPPY),
    ("a config error", "you: [first-principles]\n"),
)


class SessionStart(unittest.TestCase):
    def test_happy_path_points_at_bundled_manifestos(self):
        r = run_hook("session-start.sh", HAPPY)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn('"first-principles"', r.stdout)
        self.assertIn("Manifestos: " + PLUGIN_ROOT + "/manifestos/", r.stdout)

    def test_missing_manifesto_file_still_binds_without_cloning(self):
        r = run_hook("session-start.sh", MISSING)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn('"no-such-manifesto"', r.stdout)
        self.assertFalse(os.path.exists(os.path.join(PLUGIN_ROOT, "manifestos", "no-such-manifesto.md")))


class SessionStartSources(unittest.TestCase):
    def test_a_file_source_is_read_from_its_absolute_path_beside_the_config(self):
        r = run_hook("session-start.sh", "you:\n  - name: notes\n    purpose: house rules\n    source: file notes/rules.md\n")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn('"notes" governs your house rules \u2014 read it from ' + r.project + "/notes/rules.md.", r.stdout)

    def test_a_manifesto_source_is_read_from_the_registry_file_of_that_name(self):
        r = run_hook("session-start.sh", "you:\n  - name: again\n    source: manifesto first-principles\n")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn('"again" is part of your constitution \u2014 read it from ' + FIRST_PRINCIPLES + ".", r.stdout)

    def test_a_skill_source_is_read_from_the_skill_as_written(self):
        r = run_hook("session-start.sh", "you:\n  - name: write-well\n    source: skill agent-conduct:write-well\n")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn('"write-well" is part of your constitution \u2014 read it from skill agent-conduct:write-well.', r.stdout)

    def test_a_bare_item_with_a_colon_is_a_name_and_crashes_nothing(self):
        for script in ("session-start.sh", "post-compact.sh", "drift-reminder.sh"):
            r = run_hook(script, "you:\n  - agent-conduct:write-well\n")
            self.assertEqual(r.returncode, 0, script + r.stderr)
            self.assertIn("agent-conduct:write-well", r.stdout, script)


class SessionStartRegistry(unittest.TestCase):
    def test_a_relative_manifesto_dir_resolves_against_the_config_folder(self):
        r = run_hook("session-start.sh", "manifesto_dir: reg\nyou:\n  - name: again\n    source: manifesto first-principles\n")
        self.assertEqual(r.returncode, 0, r.stderr)
        registry = os.path.join(os.path.realpath(r.project), "reg")
        self.assertIn("read it from " + registry + "/manifestos/first-principles.md.", r.stdout)
        self.assertIn("Manifestos: " + registry + "/manifestos/", r.stdout)


class ConfigProblems(unittest.TestCase):
    def test_a_broken_config_is_named_on_stderr_and_in_the_output_form_of_every_binding_hook(self):
        r = run_hook("drift-reminder.sh", "you: [first-principles]\n")
        self.assertEqual((r.returncode, r.stdout, r.stderr), (0, "", "unharness: you must be a list of elements\n"))
        for script in BINDING_HOOKS:
            r = run_hook(script, "you: [first-principles]\n", stdin=json.dumps({"agent_type": "worker"}))
            self.assertEqual(r.returncode, 0, script)
            self.assertEqual(r.stderr, "unharness: you must be a list of elements\n", script)
            self.assertEqual(bound_line(script, r.stdout), unbound_line("you must be a list of elements"), script)

    def test_a_legacy_source_is_refused_in_one_line_in_every_binding_hook(self):
        for source in ("https://example.com/x.md", "./a.md", "some hint"):
            for script in BINDING_HOOKS:
                r = run_hook(script, "you:\n  - name: x\n    source: " + source + "\n", stdin=json.dumps({"agent_type": "worker"}))
                self.assertEqual(r.returncode, 0, script)
                self.assertEqual(len(r.stderr.splitlines()), 1, script)
                self.assertIn("write a path as file <path>", r.stderr, script)
                self.assertEqual(bound_line(script, r.stdout), unbound_line(r.stderr.removeprefix("unharness: ").rstrip("\n")), script)

    def test_an_old_layout_is_printed_whole_on_stderr_and_its_first_line_enters_the_context(self):
        for script in BINDING_HOOKS:
            r = run_hook(script, None, stdin=json.dumps({"agent_type": "worker"}), files={".manifestos.yaml": HAPPY})
            self.assertEqual(r.returncode, 0, script)
            first, *commands = r.stderr.removeprefix("unharness: ").splitlines()
            self.assertEqual(first, "old layout in " + r.project + "; run these there:", script)
            self.assertEqual(commands, ["mkdir -p .manifestos", "mv .manifestos.yaml .manifestos/config.yaml"], script)
            self.assertEqual(
                bound_line(script, r.stdout),
                f"No manifesto bound: old layout in {r.project}; run these there; run unharness doctor for the fix.", script)

    def test_drift_reminder_keeps_stderr_alone_on_an_old_layout(self):
        r = run_hook("drift-reminder.sh", None, files={".manifestos.yaml": HAPPY})
        self.assertEqual((r.returncode, r.stdout), (0, ""))
        self.assertIn("old layout in", r.stderr)

    def test_python_chatter_on_stderr_does_not_corrupt_a_valid_config(self):
        for script in ("session-start.sh", "post-compact.sh", "drift-reminder.sh"):
            r = run_hook(script, HAPPY, PYTHONVERBOSE="1")
            self.assertEqual(r.returncode, 0, script)
            self.assertIn("first-principles", r.stdout, script)

    def test_a_missing_config_stays_silent_in_every_hook(self):
        for script in ALL_HOOKS:
            r = run_hook(script, None, stdin=json.dumps({"agent_type": "worker"}))
            self.assertEqual((r.returncode, r.stdout, r.stderr), (0, "", ""), script)


class StandDownUnderUnharness(unittest.TestCase):
    def test_every_main_session_hook_prints_nothing_when_unharness_is_set(self):
        subagents = HAPPY + SUBAGENTS.format(name="first-principles")
        for script in MAIN_SESSION_HOOKS:
            r = run_hook(script, subagents, UNHARNESS="1")
            self.assertEqual((r.returncode, r.stdout, r.stderr), (0, "", ""), script)

    def test_the_subagent_hook_binds_under_unharness_exactly_as_in_a_plain_session(self):
        for label, config in SUBAGENT_BINDING_CASES:
            with self.subTest(label):
                plain = run_hook("subagent-start.sh", config, stdin=json.dumps({"agent_type": "worker"}))
                unharnessed = run_hook("subagent-start.sh", config, stdin=json.dumps({"agent_type": "worker"}), UNHARNESS="1")
                self.assertNotEqual(plain.stdout, "")
                self.assertEqual((unharnessed.returncode, unharnessed.stdout, unharnessed.stderr),
                                 (plain.returncode, plain.stdout, plain.stderr))

    def test_unharness_zero_leaves_every_hook_running(self):
        subagents = HAPPY + SUBAGENTS.format(name="first-principles")
        for script in ALL_HOOKS:
            r = run_hook(script, subagents, stdin=json.dumps({"agent_type": "worker"}), UNHARNESS="0")
            self.assertIn("first-principles", r.stdout, script)



class PostCompact(unittest.TestCase):
    def test_happy_path_emits_postcompact_json(self):
        r = run_hook("post-compact.sh", HAPPY)
        self.assertEqual(r.returncode, 0, r.stderr)
        out = json.loads(r.stdout)["hookSpecificOutput"]
        self.assertEqual(out["hookEventName"], "PostCompact")
        self.assertIn("first-principles", out["additionalContext"])

    def test_missing_manifesto_file_still_emits_json(self):
        r = run_hook("post-compact.sh", MISSING)
        self.assertEqual(r.returncode, 0, r.stderr)
        out = json.loads(r.stdout)["hookSpecificOutput"]
        self.assertIn("no-such-manifesto", out["additionalContext"])


class SubagentStart(unittest.TestCase):
    def test_happy_path_emits_subagent_json(self):
        r = run_hook("subagent-start.sh", SUBAGENTS.format(name="first-principles"),
                     stdin=json.dumps({"agent_type": "worker"}))
        self.assertEqual(r.returncode, 0, r.stderr)
        out = json.loads(r.stdout)["hookSpecificOutput"]
        self.assertEqual(out["hookEventName"], "SubagentStart")
        self.assertIn("first-principles", out["additionalContext"])

    def test_missing_manifesto_file_still_emits_json(self):
        r = run_hook("subagent-start.sh", SUBAGENTS.format(name="no-such-manifesto"),
                     stdin=json.dumps({"agent_type": "worker"}))
        self.assertEqual(r.returncode, 0, r.stderr)
        out = json.loads(r.stdout)["hookSpecificOutput"]
        self.assertIn("no-such-manifesto", out["additionalContext"])


CASCADE_ROWS = (
    ("exact", "worker", ["worker", "other"], "worker"),
    ("part after the last colon", "dev-cycle:implementer", ["implementer", "other"], "implementer"),
    ("suffix", "my-implementer", ["implementer", "other"], "implementer"),
    ("config order between two suffix keys", "code-reviewer", ["viewer", "reviewer"], "viewer"),
    ("exact other", "other", ["worker", "other"], "other"),
    ("empty type", "", ["worker", "other"], "other"),
    ("fall-through", "stranger", ["worker", "other"], "other"),
    ("no match", "stranger", ["worker"], None),
)
NO_ROLE_MATCH = "No role-specific elements matched"


class SubagentCascade(unittest.TestCase):
    def test_subagent_key_and_the_hook_choose_the_same_key_for_every_row(self):
        for label, agent_type, keys, expected in CASCADE_ROWS:
            with self.subTest(label):
                self.assertEqual(subagent_key(agent_type, keys), expected)
                config = "subagents:\n" + "".join(f"  {key}:\n    - element-of-{key}\n" for key in keys)
                r = run_hook("subagent-start.sh", config, stdin=json.dumps({"agent_type": agent_type}))
                context = json.loads(r.stdout)["hookSpecificOutput"]["additionalContext"]
                if expected is None:
                    self.assertIn(NO_ROLE_MATCH, context)
                    continue
                self.assertNotIn(NO_ROLE_MATCH, context)
                named = [key for key in keys if f'"element-of-{key}"' in context]
                self.assertEqual(named, [expected])


class BrokenCascadeImport(unittest.TestCase):
    def test_a_cascade_import_that_fails_unbinds_the_subagent_with_the_import_error(self):
        with tempfile.TemporaryDirectory() as root:
            shutil.copytree(HOOKS, os.path.join(root, "hooks"))
            package = os.path.join(root, "unharness", "src", "unharness")
            os.makedirs(package)
            with open(os.path.join(PLUGIN_ROOT, "unharness", "src", "unharness", "config.py")) as f:
                source = f.read()
            with open(os.path.join(package, "config.py"), "w") as f:
                f.write(source.replace("def subagent_key(", "def renamed_key("))
            r = run_hook("subagent-start.sh", "subagents:\n  other:\n    - x\n", stdin=json.dumps({"agent_type": "worker"}),
                         hooks=os.path.join(root, "hooks"))
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("ImportError", r.stderr)
        self.assertTrue(bound_line("subagent-start.sh", r.stdout).startswith("No manifesto bound: ImportError: cannot import name 'subagent_key'"))


class DriftReminder(unittest.TestCase):
    def test_a_name_is_matched_to_its_manifesto_file_exactly_and_never_by_title(self):
        r = run_hook("drift-reminder.sh", "you:\n  - decomplect\n")
        self.assertEqual(r.stdout.strip(), "Active bindings: decomplect")

    def test_a_manifesto_source_names_the_file_whatever_the_element_is_called(self):
        r = run_hook("drift-reminder.sh", "you:\n  - name: fp\n    source: manifesto first-principles\n")
        self.assertEqual(r.stdout.strip(), 'Active bindings: fp: "' + tagline_of(FIRST_PRINCIPLES) + '"')

    def test_a_skill_or_a_file_element_prints_its_bare_name(self):
        r = run_hook("drift-reminder.sh", "you:\n  - name: first-principles\n    source: skill a:b\n")
        self.assertEqual(r.stdout.strip(), "Active bindings: first-principles")

    def test_happy_path_prints_tagline_from_bundled_file(self):
        r = run_hook("drift-reminder.sh", HAPPY)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("Active bindings: first-principles", r.stdout)
        self.assertIn(tagline_of(FIRST_PRINCIPLES), r.stdout)

    def test_a_block_scalar_in_frontmatter_surfaces_its_message_and_the_name_prints_bare(self):
        r = run_hook("drift-reminder.sh", "manifesto_dir: reg\nyou:\n  - folded\n",
                     files={"reg/manifestos/folded.md": "---\ntagline: >\n  folded text\n---\nbody\n"}, setup_dirs=("reg/manifestos",))
        self.assertEqual((r.returncode, r.stdout.strip()), (0, "Active bindings: folded"))
        self.assertIn("key 'tagline' holds a block scalar; block scalars are not supported; write the value on one line", r.stderr)

    def test_missing_manifesto_file_prints_bare_name(self):
        r = run_hook("drift-reminder.sh", MISSING)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(r.stdout.strip(), "Active bindings: no-such-manifesto")


if __name__ == "__main__":
    unittest.main()
