# Strategy specifications

Each strategy gets a spec here **before** any code is written: `SPEC-<NNN>-<slug>.md`, copied from [`TEMPLATE.md`](TEMPLATE.md).

The spec is the contract. The implementation in `src/systrade/strategies/` must match it exactly, and any later change to the spec is recorded in its changelog.

| ID | Name | Status | Issue |
|---|---|---|---|
| SPEC-001 | Trend following (daily, long only) | planned | [#3](https://github.com/Sportx666/sistematic_trading/issues/3) |

Status values: `draft` → `approved` → `implemented` → `validated` / `rejected` → `paper` → `retired`.
