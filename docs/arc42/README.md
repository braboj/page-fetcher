# Architecture (arc42)

The architecture documentation for pagefetch, in the arc42 structure. One
file per chapter, read in order or entered at whichever chapter answers the
question at hand.

| Chapter | Answers |
| --------- | --------- |
| [1. Introduction and Goals](01_introduction_and_goals.md) | What the package does, who for, what it must get right |
| [2. Architecture Constraints](02_architecture_constraints.md) | The givens — runtime, platforms, licensing, conventions |
| [3. System Scope and Context](03_system_scope_and_context.md) | What is inside the boundary and what it exchanges across it |
| [4. Solution Strategy](04_solution_strategy.md) | Which technologies, and the approach the design rests on |
| [5. Building Block View](05_building_block_view.md) | The parts inside, what each is responsible for, what depends on what |
| [6. Runtime View](06_runtime_view.md) | The escalation ladder, and what happens during a fetch |
| [7. Deployment View](07_deployment_view.md) | Installation profiles, the environments it runs in, the gate |
| [8. Crosscutting Concepts](08_crosscutting_concepts.md) | Classification, decoding, the store, waits, configuration, ownership |
| [9. Architecture Decisions](09_architecture_decisions.md) | The index of decision records |
| [10. Quality Requirements](10_quality_requirements.md) | The quality tree and the scenarios that check it |
| [11. Risks and Technical Debt](11_risks_and_technical_debt.md) | What is known to be wrong, weak, or unmeasured |
| [12. Glossary](12_glossary.md) | The vocabulary these chapters use |
| [13. References](13_references.md) | External material worth reading alongside |

Two rules hold across every chapter. No chapter body cites a decision
record — chapter 9 is the single index. No chapter refers forward to a
higher-numbered one.

Diagrams live in [`../assets/`](../assets/), named for the chapter that
embeds them. Each is a `.drawio` source with its exported `.png` beside it,
and the chapter embeds the PNG. Sequence diagrams stay inline as Mermaid —
PLAYBOOK §4.7 has the split and the export command.
