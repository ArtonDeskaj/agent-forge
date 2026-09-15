# Evaluation report — email-urgency-router-cloud

- **Tasks:** 14
- **Passed:** 14
- **Accuracy:** 100%
- **Mean judge score:** 1.0
- **Wall time:** 184.02s

## Per task

| ID | Pass | Score | Seconds | Reason |
|----|------|-------|---------|--------|
| t1 | yes | 1.00 | 14.1 | Urgency is Critical, category is security/account takeover, escalate is true, an |
| t2 | yes | 1.00 | 13.93 | Correctly identifies High urgency, billing category, escalation to billing/refun |
| t3 | yes | 1.00 | 15.1 | Correctly classified as Low urgency and general feature request, did not escalat |
| t4 | yes | 1.00 | 9.17 | Matches expected Low urgency, low confidence, and routes to human triage without |
| t5 | yes | 1.00 | 14.92 | Urgency is High, category technical, escalate true, and the rationale cites repe |
| t6 | yes | 1.00 | 17.7 | Correctly identifies Critical urgency, legal/privacy category, escalation, and r |
| t7 | yes | 1.00 | 14.42 | Correctly identifies Medium urgency, technical category, no escalation, and next |
| t8 | yes | 1.00 | 10.73 | Urgency is Critical, escalate is true, and next_action immediately escalates to  |
| t9 | yes | 1.00 | 16.1 | Correctly identifies High urgency, account category, no escalation, and next act |
| t10 | yes | 1.00 | 12.13 | Matches expected outcome: Medium urgency, low confidence, escalate false, non-em |
| t11 | yes | 1.00 | 11.63 | Correctly marks Low urgency, general/sales-partnership category, no escalation,  |
| t12 | yes | 1.00 | 11.05 | Agent correctly marks urgency Critical, escalates true, and recommends immediate |
| t13 | yes | 1.00 | 13.47 | Urgency is Medium, escalate is false, and the rationale explicitly states the cu |
| t14 | yes | 1.00 | 9.57 | Correctly identifies low urgency, no escalation, and a close/confirmation next a |

## Harness grade

- **Tasks:** 14 (unique inputs: 14)
- **Score:** 100%
- **Substantial (>= 5 tasks):** yes
- **Every task has an expected outcome:** yes
- **Every free-form task has a success criterion:** yes
- **Inputs unique:** yes
