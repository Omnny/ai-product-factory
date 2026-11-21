# EARS — Easy Approach to Requirements Syntax

Every `REQ` **Statement** in this factory is written in EARS. EARS limits each requirement to a small set of sentence templates. This removes most ambiguity, makes triggers and preconditions explicit, and gives each requirement a ready-made test structure. `scripts/trace_check.py --gate requirements` enforces the grammar.

## The patterns

| Pattern (`EARS` field) | Template | Use for |
|---|---|---|
| `ubiquitous` | The `<system>` shall `<response>`. | Always-true properties, most non-functional requirements and constraints |
| `event-driven` | **When** `<trigger>`, the `<system>` shall `<response>`. | Responses to an event or actor action (main-flow use case steps) |
| `state-driven` | **While** `<state>`, the `<system>` shall `<response>`. | Behavior that applies for as long as the system is in a state or mode |
| `unwanted` | **If** `<condition>`, **then** the `<system>` shall `<response>`. | Errors, failures, invalid input, abuse (use case extensions) |
| `optional` | **Where** `<feature is included>`, the `<system>` shall `<response>`. | Behavior that exists only in certain configurations, editions, or platforms |
| `complex` | [**Where** …,] [**While** …,] **When** … / **If** …, then … the `<system>` shall … | Combinations, always in the order Where, then While, then When or If |

Grammar (case-insensitive keywords, optional trailing period):

```
[Where <feature>, ] [While <state>, ] [When <trigger>, | If <condition>, then ] the <system> shall <response>
```

## Rules

1. **Exactly one `shall` per statement.** If you need "and shall", write two requirements. "shall not" is allowed.
2. **Use one consistent system name.** Name the system (or the component the concept mandates) once in the glossary, for example "the app" or "the CLI", and use exactly that name in every statement.
3. **Put the conditions first.** Write "When the session is idle for 15 minutes, the app shall sign the user out", not "The app shall sign the user out when idle". A trailing "when" or "if" hides the pattern and the trigger.
4. **Make the response observable and measurable.** Use concrete values and units ("within 2 s", "error code AUTH_EXPIRED"), and no vague words (fast, easy, appropriate, user-friendly, robust, etc., and/or).
5. **Use `unwanted` for every failure behavior.** Each use case extension that handles an error becomes an `If …, then …` requirement. Don't hide error handling inside an event-driven statement.
6. **Describe states, not timing, in `While` clauses.** "While the device is offline", not "While loading takes long".
7. **Acceptance criteria stay in Given/When/Then.** EARS defines the *requirement*. The acceptance criteria give concrete examples of it, with values and boundaries.
8. Declare the pattern in the `EARS` field. The checker verifies that it matches the statement.

## From use cases to EARS

| Use case element | Typical EARS pattern |
|---|---|
| Main success step: actor action → system response | `event-driven` |
| Extension: invalid input, failure, timeout, unauthorized actor | `unwanted` |
| Behavior that depends on a mode or state (signed in, offline, editing) | `state-driven` or `complex` |
| A variant that exists only for some configurations or editions | `optional` |
| Success or minimal guarantee, business rule, quality attribute | `ubiquitous` (or `state-driven`) |

## Examples

| | Statement | Problem |
|---|---|---|
| ✗ | The system should be fast. | No "shall", nothing measurable |
| ✗ | The app shall validate the form and shall show errors. | Two "shall"s: not atomic |
| ✗ | If the card is declined, the system shall show an error. | Missing ", then" |
| ✗ | The app shall log the user out when idle. | Trigger hidden at the end; "idle" not quantified |
| ✓ | When the shopper confirms the order, the shop shall reserve every item in the cart within 2 s. | `event-driven` |
| ✓ | If the payment provider does not respond within 10 s, then the shop shall cancel the reservation and display error PAYMENT_TIMEOUT. | `unwanted` (one "shall"; the response may have several observable parts) |
| ✓ | While the device is offline, the app shall queue outgoing messages for up to 7 days. | `state-driven` |
| ✓ | Where the enterprise edition is installed, the app shall enforce single sign-on. | `optional` |
| ✓ | While the editor has unsaved changes, when the user closes the window, the editor shall ask for confirmation. | `complex` |
| ✓ | The app shall store passwords only as salted hashes using Argon2id. | `ubiquitous` (`Type: constraint`, mandated by the concept) |

## How EARS maps to tests

Requirements are verified by **acceptance tests** (the Acceptance stage is paired with Requirements in the V). Each clause becomes a part of the acceptance test:

| Clause | Test part |
|---|---|
| Where | Configuration or edition under test |
| While | Precondition setup (put the system in the state) |
| When / If | Stimulus (the event or fault to inject) |
| shall `<response>` | Assertion (the observable result) |

`unwanted` requirements are the main source of negative and fault-injection acceptance tests.
