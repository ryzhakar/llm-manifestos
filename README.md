# LLM Manifestos

Behavioral constitutions for language models

## Quick Reference

| Manifesto | Theme | Version |
|-----------|-------|---------|
| [Build For Today](plugin/manifestos/yagni.md) | Software Engineering Principles | `1.0.0` |
| [Cargo Cult Science](plugin/manifestos/cargo-cult-science.md) | Cognitive Science | `1.0.0` |
| [Code Speaks](plugin/manifestos/self-documenting-code.md) | Software Engineering Principles | `1.0.0` |
| [Correct By Construction](plugin/manifestos/correct-by-construction.md) | Software Engineering Principles | `1.0.0` |
| [Decomplect](plugin/manifestos/kiss.md) | Software Engineering Principles | `2.0.0` |
| [Knowledge Has One Home](plugin/manifestos/dry.md) | Software Engineering Principles | `1.0.0` |
| [Lines Spent](plugin/manifestos/lines-spent.md) | Software Engineering Principles | `1.0.0` |
| [Only What It Needs](plugin/manifestos/only-what-it-needs.md) | Software Engineering Principles | `1.0.0` |
| [Raise the Bar](plugin/manifestos/raise-the-bar.md) | Cognitive Science | `1.0.0` |
| [Respect the Engine](plugin/manifestos/postgres.md) | Software Engineering Principles | `1.0.0` |
| [Stop Yapping](plugin/manifestos/stop-yapping.md) | Cognitive Science | `1.0.0` |
| [The First Principles](plugin/manifestos/first-principles.md) | Cognitive Science | `1.0.1` |
| [The Simplicity Manifesto](plugin/manifestos/simple-made-easy.md) | Cognitive Science | `2.0.0` |
| [The Zen of Python](plugin/manifestos/zen-of-python.md) | Software Engineering Principles | `1.0.0` |
| [Trust Nothing, Restore Everything](plugin/manifestos/intervention.md) | Cognitive Science | `1.0.0` |

---

## 🧠 Cognitive Science
Systems for thinking


### [Cargo Cult Science](plugin/manifestos/cargo-cult-science.md) `1.0.0`
*"the first principle is that you must not fool yourself"*

Some remarks on science, pseudoscience, and learning how to not fool yourself.

---

### [Raise the Bar](plugin/manifestos/raise-the-bar.md) `1.0.0`
*"raise the bar, not the voice"*

This manifesto tells a writer how to state a demand, a belief, and the stakes, with pressure from stakes and resources rather than from contempt or threat.

---

### [Stop Yapping](plugin/manifestos/stop-yapping.md) `1.0.0`
*"answer. shut up."*

Performative helpfulness degrades accuracy. Every word past the answer is failure.

---

### [The First Principles](plugin/manifestos/first-principles.md) `1.0.1`
*"atoms, not analogies"*

Stop copying. Stop iterating. Deconstruct reality to its axioms and build the future from scratch.

---

### [The Simplicity Manifesto](plugin/manifestos/simple-made-easy.md) `2.0.0`
*"the confusion is killing you"*

Distinguishes simple (untangled) from easy (familiar). A thinking framework — the conflation is a cognitive error before it is a software defect.

---

### [Trust Nothing, Restore Everything](plugin/manifestos/intervention.md) `1.0.0`
*"roots, not canopy"*

An intervener's protocol for diagnosing and restoring corrupted systems without being absorbed by them

## 🔧 Software Engineering Principles
Core principles for building maintainable, understandable software


### [Build For Today](plugin/manifestos/yagni.md) `1.0.0`
*"build for today"*

Stop building for imagined futures. Presumptive development creates cascading costs that compound into bankruptcy.

---

### [Code Speaks](plugin/manifestos/self-documenting-code.md) `1.0.0`
*"comments are lies"*

Code should be so clear it teaches its domain without comments. Comments are admissions of defeat.

---

### [Correct By Construction](plugin/manifestos/correct-by-construction.md) `1.0.0`
*"invalid states cannot compile"*

Make invalid states unrepresentable. Every compiler error is a bug you didn't ship.

---

### [Decomplect](plugin/manifestos/kiss.md) `2.0.0`
*"incidental is Latin for your fault"*

Complexity from braiding is killing software. Concrete commands for unbraiding codebases, questioning layers, and resisting AI slop.

---

### [Knowledge Has One Home](plugin/manifestos/dry.md) `1.0.0`
*"knowledge has one home"*

Knowledge duplication (not code duplication) is the enemy. Every piece of knowledge must have one authoritative representation.

---

### [Lines Spent](plugin/manifestos/lines-spent.md) `1.0.0`
*"spent, not produced. yours, not theirs."*

Every line a model types or pulls is spent, never produced, and the one who ships it owns its cost.

---

### [Only What It Needs](plugin/manifestos/only-what-it-needs.md) `1.0.0`
*"take in what you use. expose what must go out."*

Whatever crosses a boundary is coupling: take in only the inputs you use, and hide each decision that is difficult or likely to change.

---

### [Respect the Engine](plugin/manifestos/postgres.md) `1.0.0`
*"you use 5% of what you bought."*

Postgres is a precision instrument. You use it as a filing cabinet. The schema is the architecture. The application is the view layer. Everything else you believe is wrong.

---

### [The Zen of Python](plugin/manifestos/zen-of-python.md) `1.0.0`
*"refuse to guess"*

Tim Peters' aphorisms for Python design philosophy. Explicit over implicit, simple over complex.

## Maintenance

> *Manifestos are precious artifacts, not documentation.*

This README is generated from manifesto frontmatter. **For complete maintainer workflows, see [MAINTAINERS_GUIDE.md](MAINTAINERS_GUIDE.md).**

**Install the plugin:**

```
/plugin marketplace add ryzhakar/llm-manifestos
/plugin install manifesto@llm-manifestos
```

The plugin carries `manifestos/` and `digests/` in its own folder; nothing is cloned at session start.

It also carries unharness, which compiles the manifestos a project lists in `.manifestos/config.yaml` into a session's system prompt, and with `--agent` into a subagent's, in full or, under `--digests`, as the shorter digests in `digests/` and `.manifestos/digests/`; `unharness stack --agent` prints a subagent's stack, and `unharness stack --diff` shows why a compiled file went stale. It runs through uv. See the Unharness section of [plugin/README.md](plugin/README.md).

**Quick workflow:**

1. Edit manifesto files in `plugin/manifestos/`
2. Run `just readme`
3. Commit changes

**Adding a new manifesto:**
- Create `plugin/manifestos/<name>.md` with required frontmatter (title, tagline, version, theme, description)
- If using a new theme, add it to `themes.yaml` first
- See [MAINTAINERS_GUIDE.md](MAINTAINERS_GUIDE.md) for philosophy and detailed workflows

**Schema validation:** Powered by Pydantic. Invalid frontmatter will be caught with detailed error messages.
