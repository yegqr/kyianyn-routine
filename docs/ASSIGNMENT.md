# KSE AI Agentic School: Stage 2 Assignment

Source: invitation email from the Admissions Team and the Stage 2 submission form.

## Key facts

| Item | Value |
|---|---|
| Program | KSE AI Agentic School, Stage 2 of the selection pipeline |
| Candidate email | yisakov@kse.org.ua (same as in the Stage 1 submission) |
| Deadline | Monday, 12 October 2026, 23:59 Kyiv time (EEST) |
| Language | Python |
| Task | Mini pet project: time series analysis of air raid alerts in Ukraine |
| Next stage | Stage 3: technical and motivational screening with two interviewers, including a discussion of this solution |

## Task

Build a working Python project that analyzes and forecasts air raid alerts in Ukraine as a time series.

Domain expertise in forecasting or defense analytics is not expected. AI must be the primary engineering tool used to bridge that gap, not an ornament.

## Data rules

1. Use the most recent data available.
2. Evaluate the solution on the latest period.
3. No data leakage: nothing the model is trained on or takes as input may come from after the moment the forecast is made.

### Optional: text and media data

Encouraged but not required: go beyond alert history and use text or media sources, for example:

- news
- official statements
- public Telegram channels

The same leakage rule applies: only content published before the forecast time.

## Deliverables

Submitted via the Stage 2 form. All fields are required.

| # | Field | What to submit |
|---|---|---|
| 1 | Email | yisakov@kse.org.ua |
| 2 | GitHub repository link | Public repo with the final, working Python code |
| 3 | AI conversation log | Full text export of the conversation history with the chosen AI tool (Claude, ChatGPT, Gemini, etc.), complete |
| 4 | Project reflection | Plain text, about 100 words, answering the three questions below |

### Reflection questions

1. What went wrong?
2. How did you adjust your approach?
3. Why is your final version better than your first attempt?

## How it is evaluated

The process is evaluated, not just the result. The AI interaction log is the primary signal. Reviewers look for a candidate who:

- actively iterates
- challenges model hallucinations
- corrects errors
- guides the AI toward a functional architecture instead of blindly accepting the first output

## Checklist before submitting

- [ ] Repository is public and the code runs end to end
- [ ] Latest available data is used; evaluation is on the most recent period
- [ ] No leakage: features and training data are strictly before forecast time (including any text/media data)
- [ ] AI conversation log exported in full
- [ ] Reflection written (~100 words, plain text, all three questions)
- [ ] Form submitted from yisakov@kse.org.ua before 12 Oct 2026, 23:59 EEST
