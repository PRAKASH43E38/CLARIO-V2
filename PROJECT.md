# CLARIO V2 Product Specification

This document follows the latest CLARIO V2 Master Prompt. Older plans and naming are historical where they conflict with this specification.

## Product promise

CLARIO is an interactive learning product that adapts explanations, practice, and progression using learner context and demonstrated understanding. The core cycle is:

**Learn → Interact → Respond → Feedback → Progress → Mastery**

## Learner journey

1. User registers/signs in and completes a personal profile.
2. User answers the one-time Mind Profile questions.
3. For each new learning session, the learner provides exactly:
   - **Task**
   - **Goal**
   - **Learner State**
   - **Interest**
4. CALA prepares a plan from these inputs and available learner evidence.
5. CLARIO-AI will coordinate research, roadmap, teaching, practice, assessment, evaluation, and progression.
6. Learner work produces evidence; CLARIO-AI advances, targets remediation, or completes the level/topic.

There is no manual “Your Level” input. Learner level is to be inferred from onboarding Mind Profile evidence, Task, Goal, Learner State, Interest, ongoing performance, concept mastery, confidence, engagement, and difficulty fit.

## Target orchestration

CLARIO-AI is the only global orchestrator and decision engine. Specialized workers are:

- **Nova** — research
- **Mira** — teaching
- **Ayan** — critical thinking
- **Kira** — practical/real-world application
- **Zayn** — assessment/challenges
- **Elara** — evaluation

The target research flow is four inputs/context → CLARIO-AI → Nova → Tavily/web search → relevance validation and query refinement → validated sources (up to ten when enough quality sources exist) → shared research package. Sources must be genuine and never fabricated.

The learning cycle is:

**Plan → Teach → Think → Apply → Quiz → Evaluate → Remediate OR Advance**

When a concept is weak, CLARIO-AI isolates it, reduces its difficulty as appropriate, reteaches with a different explanation/example, retests, and reevaluates. Mastered concepts are retained; the journey is not restarted.

## Product experience

The target UI includes a visual roadmap, levels, interactive lessons, immediate feedback, source container, concept mastery, responsive layouts, and persisted XP, streaks, daily goals, and achievements. Gamified elements must reflect persisted learner activity rather than decorative/hard-coded metrics. CLARIO uses an original green-forward visual identity.

## Current implementation (verified scope)

Implemented foundation: email/password registration/login with hashed passwords; personal profile; one-time five-answer Mind Profile; strict per-session four-input persistence; seeded Decision Trees curriculum; React/Vite frontend; FastAPI/SQLAlchemy backend; single SQLite database; legacy generic agent and adaptive-policy code.

The four-input session path creates a legacy learner-profile anchor so concept performance can be stored. Its compatibility fields do not represent a dynamic learner model. CALA creates a deterministic, session-specific structured plan and initial roadmap; Level 1 is unlocked and later levels remain locked without mapped mastery evidence. It defaults safely to Beginner when level evidence is insufficient and leaves confidence/weakness unknown when evidence is absent. CLARIO-AI persists the session workflow state, loads the saved CALA plan, dispatches research through an internal boundary to Nova, then dispatches teaching to Mira using the same session's saved plan and SharedResearchPackage. Mira returns typed content and validated source references, which CLARIO-AI persists with `TEACHING_READY`. The frontend communicates with CLARIO-AI and displays both the research package and teaching response. Automated query refinement and later learning-agent execution are not implemented.

The current vertical slice dispatches Nova research, Mira teaching, Ayan reasoning-prompt generation, Kira practical-activity generation, Zayn quiz generation/submission, and Elara evaluation through CLARIO-AI. Zayn answer keys remain private. Elara evaluates teaching coverage and submitted quiz metrics; Ayan/Kira learner responses are unavailable and are not fabricated. Elara does not decide progression or remediation; CLARIO-AI's post-evaluation decision remains unimplemented. Automated query refinement, ongoing dynamic level inference, three-database storage, persisted gamification, and final reporting remain unimplemented. Authentication is not yet secure session/token authentication, and Google OAuth is unavailable. Tavily access requires a backend `TAVILY_API_KEY`; no source is fabricated when no candidate passes validation.
