# Datastar + Shadow DOM Web Component Examples

Experiments exploring how to use [Datastar](https://data-star.dev/) (a hypermedia
framework) with Web Components and Shadow DOM.

## The Problem

Datastar works by walking the DOM tree for `data-*` attributes. Shadow DOM creates
encapsulated subtrees that Datastar's walker **cannot see into by default**. These
examples explore three approaches to bridging this gap.

## Examples

### 01_light_dom.html — Light DOM (no Shadow DOM)
**Simplest approach.** Custom elements render into the light DOM so Datastar
processes their `data-*` attributes normally. No special handling needed.

Open directly in a browser — no server required.

### 02_shadow_dom.html — Shadow DOM + Manual Apply
Uses `attachShadow()` for style encapsulation, then calls `Datastar.apply(shadowRoot)`
to tell Datastar to process the shadow content. Signals are global (shared namespace).

Open directly in a browser — no server required.

### 03_sse_shadow_dom.html — Shadow DOM + SSE Backend
Combines Shadow DOM web components with server-sent events. A Python backend
streams simulated EEG data that updates both regular DOM and shadow DOM content.

**Requires the server:**
```bash
python server.py
# Open http://localhost:8000/03_sse_shadow_dom.html
```

## Key Findings

| Approach | Shadow DOM? | Signal Scoping | Complexity |
|---|---|---|---|
| Light DOM custom elements | No | Global (shared) | None |
| Manual `Datastar.apply()` | Yes | Global (shared) | Low |
| [datastar-components plugin](https://github.com/aereaco/datastar-components) | Yes | Props-based | Medium |
| [Rocket (Datastar Pro)](https://data-star.dev/reference/rocket) | Opt-in | `$$` scoped | Medium |

## Notes

- `Datastar.apply(shadowRoot)` is the key API for Shadow DOM integration
- Signal names are global — two shadow components declaring `localCount` would collide
- For true signal scoping, use Datastar Pro's Rocket or the community datastar-components plugin
- The SSE protocol uses `event: datastar-merge-signals` with `data: signals {json}`
