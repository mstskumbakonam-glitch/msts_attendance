# Token Optimization Guide

Instruction manual for the AI coding agent working on this project.

---

## 1. Purpose

Maximize useful work per token while maintaining correctness, security, code quality, and project requirements.

---

## 2. Core Principle

> **"Think carefully before acting, then execute the smallest reliable set of actions needed to complete the task."**

Token optimization reduces *unnecessary work*. It never reduces the quality of reasoning or implementation.

---

## 3. Efficient Project Exploration

- Inspect only files relevant to the current task.
- Do not re-read unchanged files.
- Use targeted searches (e.g., grep for a symbol or string) instead of scanning the whole repository.
- Understand the existing architecture before modifying it.
- Reuse information already obtained during the current task.
- Do not explore unrelated directories.

---

## 4. Efficient Implementation

- Make the smallest reliable change required.
- Reuse existing code, utilities, components, and services.
- Do not refactor unless the task requires it.
- Do not add abstractions without a concrete need.
- Do not duplicate existing implementations.
- Do not generate boilerplate that provides no value.
- Keep implementations simple, maintainable, and production-ready.
- Modify only files necessary for the task.

---

## 5. Efficient Tool Usage

- Do not run unnecessary commands.
- Do not re-run a command whose result is already known.
- Run targeted tests instead of the entire suite when appropriate.
- Avoid unnecessary builds, scans, dependency installations, and environment checks.
- Combine related operations when practical.
- Stop exploring once you have sufficient information.

---

## 6. Efficient Error Handling

Workflow:

1. Read the actual error.
2. Identify the likely root cause.
3. Inspect only the relevant code/configuration.
4. Make the smallest effective fix.
5. Run the minimum verification required.
6. If the fix fails, reassess instead of repeatedly applying random changes.

Do not generate multiple speculative solutions unless the first approach fails.

---

## 7. Context Management

- Do not repeat project requirements back.
- Do not restate large portions of files.
- Keep working context focused on the current task.
- Summarize large command outputs instead of reproducing them.
- Reference existing documentation instead of rewriting it.
- Treat the project's main specification/documentation as the source of truth.

---

## 8. Code Generation Rules

- Generate only the code required for the current task.
- Prefer concise implementations.
- Follow existing project conventions.
- Avoid unnecessary comments.
- Avoid unnecessary helper functions.
- Avoid duplicate logic.
- Do not create unused variables, imports, dependencies, or files.
- Do not generate placeholder functionality unless explicitly requested.

---

## 9. Dependency Optimization

- Reuse existing dependencies whenever possible.
- Do not add a new library when the existing stack can solve the problem.
- Do not install dependencies without a clear requirement.
- Before adding a dependency, check whether an existing project dependency already provides the functionality.
- Keep the dependency footprint reasonable.

---

## 10. Testing and Verification

Testing should be efficient but sufficient.

- Test the changed functionality first.
- Run focused tests when possible.
- Run broader tests when the change affects shared/core functionality.
- Do not re-run tests that already passed unless relevant code has changed.
- Never skip important verification merely to save tokens.

---

## 11. Git and Team Efficiency

- Work only on the assigned branch/task.
- Do not overwrite other developers' work.
- Keep commits focused.
- Do not mix unrelated changes in one commit.
- Do not rewrite working code unnecessarily.
- Review the diff before committing.
- Do not force-push unless explicitly instructed.
- Do not modify unrelated files.

---

## 12. Avoiding AI Wasted Work

Avoid these common inefficient behaviors:

- Re-reading the same files repeatedly.
- Rewriting working code without a reason.
- Creating unnecessary architecture.
- Overengineering simple features.
- Installing unnecessary packages.
- Running unrelated tests.
- Repeating failed commands without changing the approach.
- Generating extremely long explanations.
- Making changes outside the requested scope.
- Exploring alternatives indefinitely after a valid solution is available.

---

## 13. When to Ask for Clarification

Do **not** ask unnecessary questions when the requirement is already clear.

**Ask when:**

- A decision significantly affects the architecture.
- Multiple interpretations would produce substantially different implementations.
- Required information is genuinely missing.
- A change could cause data loss, security issues, or major project disruption.

Otherwise, choose the simplest reasonable implementation and proceed.

---

## 14. Response Efficiency

After completing a task, provide a concise summary containing only:

### Changed
What was changed.

### Files
Which files were modified/created.

### Verification
What was tested or verified.

### Remaining Issues
Only actual unresolved issues or blockers.

Do not provide long explanations unless specifically requested.

---

## 15. Quality Must Not Be Sacrificed

Token optimization must **never** mean:

- Skipping necessary reasoning.
- Skipping security checks.
- Skipping important tests.
- Ignoring errors.
- Reducing code quality.
- Removing necessary documentation.
- Making unsafe assumptions.
- Cutting corners on requirements.

The objective is:

> **"Less unnecessary work, not less necessary work."**

---

## 16. Project-Specific Rule

The project's main Markdown specification is the **source of truth**.

The agent must:

- Follow the documented requirements.
- Preserve the intended project scope.
- Not invent undocumented features.
- Distinguish between confirmed requirements and implementation decisions.
- Ask before making major architectural changes.

---

## 17. Final Efficiency Checklist

Mentally verify before completing a task:

- [ ] Did I inspect only relevant files?
- [ ] Did I understand the existing implementation?
- [ ] Did I avoid unnecessary changes?
- [ ] Did I reuse existing code?
- [ ] Did I avoid unnecessary dependencies?
- [ ] Did I avoid unrelated refactoring?
- [ ] Did I run only relevant verification?
- [ ] Did I review the changes?
- [ ] Did I stay within the requested scope?
- [ ] Did I keep the final response concise?
