# {{ project.title }}

{{ project.description }}

## Quick Reference

| Manifesto | Theme | Version |
|-----------|-------|---------|
{% for m in manifestos | sort(attribute='title') -%}
| [{{ m.title }}]({{ m.path }}) | {{ themes[m.theme].name if m.theme in themes else m.theme }} | `{{ m.version }}` |
{% endfor %}
---
{%- for theme_key in manifestos | map(attribute='theme') | unique | list | sort %}
{%- set theme = themes[theme_key] if theme_key in themes else {'icon': '📄', 'name': theme_key, 'description': ''} %}

## {{ theme.icon }} {{ theme.name }}
{% if theme.description -%}
{{ theme.description }}
{% endif -%}
{%- for m in manifestos | selectattr('theme', 'equalto', theme_key) | sort(attribute='title') %}

### [{{ m.title }}]({{ m.path }}) `{{ m.version }}`
*"{{ m.tagline }}"*

{{ m.description }}
{%- if not loop.last %}

---
{%- endif -%}
{%- endfor -%}
{%- endfor %}

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
