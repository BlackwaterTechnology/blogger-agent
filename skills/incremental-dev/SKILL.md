name: incremental-dev
description: Disciplined, step-by-step automation development. Mandates granular task decomposition, continuous verification via screenshots, and unit testing for every UI interaction. Prevents "black box" failures in complex browser/OS automation flows. Activates when starting new automation features or debugging stuck flows.

# Incremental Development Skill (Step-by-Step Automation)

This skill enforces a high-integrity workflow for developing complex browser and OS-level automation. It is designed to replace "big bang" coding with a "verify-at-every-click" philosophy.

## The Mandates

1.  **Decompose First**: Break every complex flow into atomic UI actions (e.g., "Click Upload", "Type Path", "Confirm Dialog").
2.  **Verify or Die**: For every action, you MUST verify the result before moving to the next.
    *   **Browser**: Use JXA/JS to check for element existence or state changes.
    *   **OS/Dialogs**: Use `peekaboo image` to take a screenshot after the action.
3.  **No Blind Typing**: Before typing or sending hotkeys, use `peekaboo app switch` and check if the target window/input is actually focused.
4.  **Traceable Debugging**: Always save screenshots of failures and intermediate states to a dedicated `screenshots/` directory for analysis.

## Workflow Pattern

### Phase 1: Exploration & Sniffing
Use `peekaboo see` or JXA snippets to "sniff" the target elements. Record their coordinates and stable selectors.

### Phase 2: Incremental Scripting (The Loop)
For each atomic action:
1.  **Draft**: Write a minimal Python/JS snippet for just that one action.
2.  **Execute**: Run the snippet.
3.  **Capture**: `peekaboo image --path screenshots/step_N_verification.png`.
4.  **Assert**: Check the screenshot or DOM state. If it matches the expected outcome, proceed. If not, fix the snippet and restart from the last known good state.

### Phase 3: Consolidation
Once the chain of atomic actions is verified, wrap them into a formal method/class (e.g., `WechatVideoPublisher`).

## When to Activate

- When developing a new platform publisher.
- When an existing automation script is "getting stuck" without clear errors.
- When interacting with native macOS dialogs (file pickers, permissions) that cannot be inspected via standard DevTools.

## Verification Checklist

- [ ] Did I take a screenshot after clicking that button?
- [ ] Is the dialog actually gone?
- [ ] Did the text field actually receive the input?
- [ ] Have I handled the "fallback" if the element doesn't appear in 5 seconds?

## Autonomy Rules

**Mandatory Action**:
- Always run `mkdir -p screenshots` at the start of a session.
- Always include `subprocess.run(["peekaboo", "image", ...])` after any `peekaboo click` or `press return`.
