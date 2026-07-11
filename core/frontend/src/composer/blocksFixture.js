// DEV FALLBACK ONLY.
//
// Regenerated verbatim from a live GET /api/blocks response (backend Order 8,
// served by ets.web.handlers / ets.web.server via web/routes.py — the
// backend is authoritative, test-asserted against config_io ground truth in
// tests/test_blocks_catalogue.py). This fixture exists purely so the
// Composer view has something to render when the backend is not reachable
// in a given dev environment. composer/api.js always prefers the live
// endpoint and only falls back to this file when the request fails, 404s,
// or does not return JSON (e.g. a bare `vite dev` server with no backend
// attached, which answers unknown paths with its index.html at 200).
//
// Do not hand-edit block shape here — if the backend catalogue changes,
// regenerate this file from a live /api/blocks response instead of
// reconciling by hand. Vocabulary notes (differ from earlier drafts of this
// file):
//   - category is 'price_formation' (underscore), matching the backend enum.
//   - param.type is Python-style: 'str' | 'float' | 'int' | 'bool' | 'list' |
//     'dict' | 'enum' — not JS-style 'string'/'number'/'boolean'.
//   - config_key is the flat config_io field name ('total_cap'), never a
//     JSON path ('years[].total_cap'); 'scope' disambiguates where it lives.
//   - scope is exactly one of: scenario | year | participant | edge.
//   - output port 'type' / input port 'accepts' entries are short kind
//     strings ('compliance', 'member_of', 'strategic', 'results', 'policy',
//     'price_formation', 'expectations', 'baseline', 'sector_pool',
//     'technology_option') — matched by type/accepts membership, never by
//     port name.

const BLOCKS_FIXTURE = [
  {
    "id": "carbon_market",
    "label": "Carbon Market",
    "category": "market",
    "doc": "One node = one scenario in {'scenarios': [...]} (config_io/builder.py:build_market_from_year).",
    "params": [
      {
        "name": "name",
        "type": "str",
        "default": "New Scenario",
        "unit": null,
        "min": null,
        "max": null,
        "enum": null,
        "config_key": "name",
        "scope": "scenario"
      },
      {
        "name": "years",
        "type": "list",
        "default": [],
        "unit": null,
        "min": null,
        "max": null,
        "enum": null,
        "config_key": "years",
        "scope": "scenario"
      },
      {
        "name": "sectors",
        "type": "list",
        "default": [],
        "unit": null,
        "min": null,
        "max": null,
        "enum": null,
        "config_key": "sectors",
        "scope": "scenario"
      },
      {
        "name": "policy_events",
        "type": "list",
        "default": [],
        "unit": null,
        "min": null,
        "max": null,
        "enum": null,
        "config_key": "policy_events",
        "scope": "scenario"
      }
    ],
    "ports": {
      "inputs": [
        {
          "name": "participants",
          "accepts": [
            "compliance"
          ],
          "cardinality": "1..n"
        },
        {
          "name": "sectors",
          "accepts": [
            "sector_pool"
          ],
          "cardinality": "0..n"
        },
        {
          "name": "price_formation",
          "accepts": [
            "price_formation"
          ],
          "cardinality": "1"
        },
        {
          "name": "policies",
          "accepts": [
            "policy"
          ],
          "cardinality": "0..n"
        },
        {
          "name": "expectations",
          "accepts": [
            "expectations"
          ],
          "cardinality": "0..1"
        },
        {
          "name": "baseline",
          "accepts": [
            "baseline"
          ],
          "cardinality": "0..1"
        }
      ],
      "outputs": [
        {
          "name": "results",
          "type": "results"
        }
      ]
    },
    "constraints": []
  },
  {
    "id": "competitive_clearing",
    "label": "Competitive Clearing",
    "category": "price_formation",
    "doc": "solvers/simulation.py:solve_scenario_path, market/equilibrium.py:solve_equilibrium",
    "params": [
      {
        "name": "model_approach",
        "type": "enum",
        "default": "competitive",
        "unit": null,
        "min": null,
        "max": null,
        "enum": [
          "competitive",
          "hotelling",
          "banking",
          "nash_cournot",
          "all"
        ],
        "config_key": "model_approach",
        "scope": "scenario"
      },
      {
        "name": "solver_competitive_max_iters",
        "type": "int",
        "default": 25,
        "unit": null,
        "min": null,
        "max": null,
        "enum": null,
        "config_key": "solver_competitive_max_iters",
        "scope": "scenario"
      },
      {
        "name": "solver_competitive_tolerance",
        "type": "float",
        "default": 0.001,
        "unit": null,
        "min": null,
        "max": null,
        "enum": null,
        "config_key": "solver_competitive_tolerance",
        "scope": "scenario"
      },
      {
        "name": "discount_rate",
        "type": "float",
        "default": 0.04,
        "unit": "1/yr",
        "min": null,
        "max": null,
        "enum": null,
        "config_key": "discount_rate",
        "scope": "scenario"
      },
      {
        "name": "risk_premium",
        "type": "float",
        "default": 0,
        "unit": "1/yr",
        "min": null,
        "max": null,
        "enum": null,
        "config_key": "risk_premium",
        "scope": "scenario"
      },
      {
        "name": "solver_penalty_price_multiplier",
        "type": "float",
        "default": 1.25,
        "unit": null,
        "min": null,
        "max": null,
        "enum": null,
        "config_key": "solver_penalty_price_multiplier",
        "scope": "scenario"
      },
      {
        "name": "solver_price_bracket_expand_factor",
        "type": "float",
        "default": 2,
        "unit": null,
        "min": null,
        "max": null,
        "enum": null,
        "config_key": "solver_price_bracket_expand_factor",
        "scope": "scenario"
      },
      {
        "name": "solver_price_bracket_max_expansions",
        "type": "int",
        "default": 10,
        "unit": null,
        "min": null,
        "max": null,
        "enum": null,
        "config_key": "solver_price_bracket_max_expansions",
        "scope": "scenario"
      },
      {
        "name": "solver_slsqp_max_iters",
        "type": "int",
        "default": 400,
        "unit": null,
        "min": null,
        "max": null,
        "enum": null,
        "config_key": "solver_slsqp_max_iters",
        "scope": "scenario"
      },
      {
        "name": "solver_slsqp_ftol",
        "type": "float",
        "default": 1e-9,
        "unit": null,
        "min": null,
        "max": null,
        "enum": null,
        "config_key": "solver_slsqp_ftol",
        "scope": "scenario"
      },
      {
        "name": "solver_calibration_xatol",
        "type": "float",
        "default": 0.1,
        "unit": null,
        "min": null,
        "max": null,
        "enum": null,
        "config_key": "solver_calibration_xatol",
        "scope": "scenario"
      },
      {
        "name": "solver_calibration_fatol",
        "type": "float",
        "default": 0.01,
        "unit": null,
        "min": null,
        "max": null,
        "enum": null,
        "config_key": "solver_calibration_fatol",
        "scope": "scenario"
      }
    ],
    "ports": {
      "inputs": [],
      "outputs": [
        {
          "name": "price_formation",
          "type": "price_formation"
        }
      ]
    },
    "constraints": []
  },
  {
    "id": "rubin_schennach_banking",
    "label": "Rubin/Schennach Banking Equilibrium",
    "category": "price_formation",
    "doc": "solvers/banking.py:solve_banking_path",
    "params": [
      {
        "name": "model_approach",
        "type": "enum",
        "default": "banking",
        "unit": null,
        "min": null,
        "max": null,
        "enum": [
          "competitive",
          "hotelling",
          "banking",
          "nash_cournot",
          "all"
        ],
        "config_key": "model_approach",
        "scope": "scenario"
      },
      {
        "name": "banking_initial_bank",
        "type": "float",
        "default": 0,
        "unit": "Mt CO2e",
        "min": null,
        "max": null,
        "enum": null,
        "config_key": "banking_initial_bank",
        "scope": "scenario"
      },
      {
        "name": "banking_strict_no_arbitrage",
        "type": "bool",
        "default": true,
        "unit": null,
        "min": null,
        "max": null,
        "enum": null,
        "config_key": "banking_strict_no_arbitrage",
        "scope": "scenario"
      },
      {
        "name": "banking_bank_tolerance",
        "type": "float",
        "default": 0.000001,
        "unit": null,
        "min": null,
        "max": null,
        "enum": null,
        "config_key": "banking_bank_tolerance",
        "scope": "scenario"
      },
      {
        "name": "banking_supply_rule_max_iters",
        "type": "int",
        "default": 25,
        "unit": null,
        "min": null,
        "max": null,
        "enum": null,
        "config_key": "banking_supply_rule_max_iters",
        "scope": "scenario"
      },
      {
        "name": "banking_supply_rule_tolerance",
        "type": "float",
        "default": 0.001,
        "unit": null,
        "min": null,
        "max": null,
        "enum": null,
        "config_key": "banking_supply_rule_tolerance",
        "scope": "scenario"
      },
      {
        "name": "discount_rate",
        "type": "float",
        "default": 0.04,
        "unit": "1/yr",
        "min": null,
        "max": null,
        "enum": null,
        "config_key": "discount_rate",
        "scope": "scenario"
      },
      {
        "name": "risk_premium",
        "type": "float",
        "default": 0,
        "unit": "1/yr",
        "min": null,
        "max": null,
        "enum": null,
        "config_key": "risk_premium",
        "scope": "scenario"
      },
      {
        "name": "solver_penalty_price_multiplier",
        "type": "float",
        "default": 1.25,
        "unit": null,
        "min": null,
        "max": null,
        "enum": null,
        "config_key": "solver_penalty_price_multiplier",
        "scope": "scenario"
      },
      {
        "name": "solver_price_bracket_expand_factor",
        "type": "float",
        "default": 2,
        "unit": null,
        "min": null,
        "max": null,
        "enum": null,
        "config_key": "solver_price_bracket_expand_factor",
        "scope": "scenario"
      },
      {
        "name": "solver_price_bracket_max_expansions",
        "type": "int",
        "default": 10,
        "unit": null,
        "min": null,
        "max": null,
        "enum": null,
        "config_key": "solver_price_bracket_max_expansions",
        "scope": "scenario"
      },
      {
        "name": "solver_slsqp_max_iters",
        "type": "int",
        "default": 400,
        "unit": null,
        "min": null,
        "max": null,
        "enum": null,
        "config_key": "solver_slsqp_max_iters",
        "scope": "scenario"
      },
      {
        "name": "solver_slsqp_ftol",
        "type": "float",
        "default": 1e-9,
        "unit": null,
        "min": null,
        "max": null,
        "enum": null,
        "config_key": "solver_slsqp_ftol",
        "scope": "scenario"
      },
      {
        "name": "solver_calibration_xatol",
        "type": "float",
        "default": 0.1,
        "unit": null,
        "min": null,
        "max": null,
        "enum": null,
        "config_key": "solver_calibration_xatol",
        "scope": "scenario"
      },
      {
        "name": "solver_calibration_fatol",
        "type": "float",
        "default": 0.01,
        "unit": null,
        "min": null,
        "max": null,
        "enum": null,
        "config_key": "solver_calibration_fatol",
        "scope": "scenario"
      }
    ],
    "ports": {
      "inputs": [],
      "outputs": [
        {
          "name": "price_formation",
          "type": "price_formation"
        }
      ]
    },
    "constraints": []
  },
  {
    "id": "hotelling",
    "label": "Hotelling Exhaustible-Resource Path",
    "category": "price_formation",
    "doc": "solvers/hotelling.py:solve_hotelling_path",
    "params": [
      {
        "name": "model_approach",
        "type": "enum",
        "default": "hotelling",
        "unit": null,
        "min": null,
        "max": null,
        "enum": [
          "competitive",
          "hotelling",
          "banking",
          "nash_cournot",
          "all"
        ],
        "config_key": "model_approach",
        "scope": "scenario"
      },
      {
        "name": "solver_hotelling_max_bisection_iters",
        "type": "int",
        "default": 80,
        "unit": null,
        "min": null,
        "max": null,
        "enum": null,
        "config_key": "solver_hotelling_max_bisection_iters",
        "scope": "scenario"
      },
      {
        "name": "solver_hotelling_max_lambda_expansions",
        "type": "int",
        "default": 20,
        "unit": null,
        "min": null,
        "max": null,
        "enum": null,
        "config_key": "solver_hotelling_max_lambda_expansions",
        "scope": "scenario"
      },
      {
        "name": "solver_hotelling_convergence_tol",
        "type": "float",
        "default": 0.0001,
        "unit": null,
        "min": null,
        "max": null,
        "enum": null,
        "config_key": "solver_hotelling_convergence_tol",
        "scope": "scenario"
      },
      {
        "name": "solver_hotelling_lambda_initial_low",
        "type": "float",
        "default": 0.001,
        "unit": null,
        "min": null,
        "max": null,
        "enum": null,
        "config_key": "solver_hotelling_lambda_initial_low",
        "scope": "scenario"
      },
      {
        "name": "solver_hotelling_lambda_initial_high",
        "type": "float",
        "default": 20,
        "unit": null,
        "min": null,
        "max": null,
        "enum": null,
        "config_key": "solver_hotelling_lambda_initial_high",
        "scope": "scenario"
      },
      {
        "name": "solver_hotelling_lambda_expand_factor",
        "type": "float",
        "default": 3,
        "unit": null,
        "min": null,
        "max": null,
        "enum": null,
        "config_key": "solver_hotelling_lambda_expand_factor",
        "scope": "scenario"
      },
      {
        "name": "discount_rate",
        "type": "float",
        "default": 0.04,
        "unit": "1/yr",
        "min": null,
        "max": null,
        "enum": null,
        "config_key": "discount_rate",
        "scope": "scenario"
      },
      {
        "name": "risk_premium",
        "type": "float",
        "default": 0,
        "unit": "1/yr",
        "min": null,
        "max": null,
        "enum": null,
        "config_key": "risk_premium",
        "scope": "scenario"
      },
      {
        "name": "solver_penalty_price_multiplier",
        "type": "float",
        "default": 1.25,
        "unit": null,
        "min": null,
        "max": null,
        "enum": null,
        "config_key": "solver_penalty_price_multiplier",
        "scope": "scenario"
      },
      {
        "name": "solver_price_bracket_expand_factor",
        "type": "float",
        "default": 2,
        "unit": null,
        "min": null,
        "max": null,
        "enum": null,
        "config_key": "solver_price_bracket_expand_factor",
        "scope": "scenario"
      },
      {
        "name": "solver_price_bracket_max_expansions",
        "type": "int",
        "default": 10,
        "unit": null,
        "min": null,
        "max": null,
        "enum": null,
        "config_key": "solver_price_bracket_max_expansions",
        "scope": "scenario"
      },
      {
        "name": "solver_slsqp_max_iters",
        "type": "int",
        "default": 400,
        "unit": null,
        "min": null,
        "max": null,
        "enum": null,
        "config_key": "solver_slsqp_max_iters",
        "scope": "scenario"
      },
      {
        "name": "solver_slsqp_ftol",
        "type": "float",
        "default": 1e-9,
        "unit": null,
        "min": null,
        "max": null,
        "enum": null,
        "config_key": "solver_slsqp_ftol",
        "scope": "scenario"
      },
      {
        "name": "solver_calibration_xatol",
        "type": "float",
        "default": 0.1,
        "unit": null,
        "min": null,
        "max": null,
        "enum": null,
        "config_key": "solver_calibration_xatol",
        "scope": "scenario"
      },
      {
        "name": "solver_calibration_fatol",
        "type": "float",
        "default": 0.01,
        "unit": null,
        "min": null,
        "max": null,
        "enum": null,
        "config_key": "solver_calibration_fatol",
        "scope": "scenario"
      }
    ],
    "ports": {
      "inputs": [],
      "outputs": [
        {
          "name": "price_formation",
          "type": "price_formation"
        }
      ]
    },
    "constraints": []
  },
  {
    "id": "nash_cournot",
    "label": "Nash–Cournot",
    "category": "price_formation",
    "doc": "solvers/nash.py:solve_nash_path",
    "params": [
      {
        "name": "model_approach",
        "type": "enum",
        "default": "nash_cournot",
        "unit": null,
        "min": null,
        "max": null,
        "enum": [
          "competitive",
          "hotelling",
          "banking",
          "nash_cournot",
          "all"
        ],
        "config_key": "model_approach",
        "scope": "scenario"
      },
      {
        "name": "solver_nash_price_step",
        "type": "float",
        "default": 0.5,
        "unit": null,
        "min": null,
        "max": null,
        "enum": null,
        "config_key": "solver_nash_price_step",
        "scope": "scenario"
      },
      {
        "name": "solver_nash_max_iters",
        "type": "int",
        "default": 120,
        "unit": null,
        "min": null,
        "max": null,
        "enum": null,
        "config_key": "solver_nash_max_iters",
        "scope": "scenario"
      },
      {
        "name": "solver_nash_convergence_tol",
        "type": "float",
        "default": 0.001,
        "unit": null,
        "min": null,
        "max": null,
        "enum": null,
        "config_key": "solver_nash_convergence_tol",
        "scope": "scenario"
      },
      {
        "name": "solver_nash_inner_xatol",
        "type": "float",
        "default": 0.0001,
        "unit": null,
        "min": null,
        "max": null,
        "enum": null,
        "config_key": "solver_nash_inner_xatol",
        "scope": "scenario"
      },
      {
        "name": "nash_strategic_participants",
        "type": "list",
        "default": [],
        "unit": null,
        "min": null,
        "max": null,
        "enum": null,
        "config_key": "nash_strategic_participants",
        "scope": "scenario"
      },
      {
        "name": "discount_rate",
        "type": "float",
        "default": 0.04,
        "unit": "1/yr",
        "min": null,
        "max": null,
        "enum": null,
        "config_key": "discount_rate",
        "scope": "scenario"
      },
      {
        "name": "risk_premium",
        "type": "float",
        "default": 0,
        "unit": "1/yr",
        "min": null,
        "max": null,
        "enum": null,
        "config_key": "risk_premium",
        "scope": "scenario"
      },
      {
        "name": "solver_penalty_price_multiplier",
        "type": "float",
        "default": 1.25,
        "unit": null,
        "min": null,
        "max": null,
        "enum": null,
        "config_key": "solver_penalty_price_multiplier",
        "scope": "scenario"
      },
      {
        "name": "solver_price_bracket_expand_factor",
        "type": "float",
        "default": 2,
        "unit": null,
        "min": null,
        "max": null,
        "enum": null,
        "config_key": "solver_price_bracket_expand_factor",
        "scope": "scenario"
      },
      {
        "name": "solver_price_bracket_max_expansions",
        "type": "int",
        "default": 10,
        "unit": null,
        "min": null,
        "max": null,
        "enum": null,
        "config_key": "solver_price_bracket_max_expansions",
        "scope": "scenario"
      },
      {
        "name": "solver_slsqp_max_iters",
        "type": "int",
        "default": 400,
        "unit": null,
        "min": null,
        "max": null,
        "enum": null,
        "config_key": "solver_slsqp_max_iters",
        "scope": "scenario"
      },
      {
        "name": "solver_slsqp_ftol",
        "type": "float",
        "default": 1e-9,
        "unit": null,
        "min": null,
        "max": null,
        "enum": null,
        "config_key": "solver_slsqp_ftol",
        "scope": "scenario"
      },
      {
        "name": "solver_calibration_xatol",
        "type": "float",
        "default": 0.1,
        "unit": null,
        "min": null,
        "max": null,
        "enum": null,
        "config_key": "solver_calibration_xatol",
        "scope": "scenario"
      },
      {
        "name": "solver_calibration_fatol",
        "type": "float",
        "default": 0.01,
        "unit": null,
        "min": null,
        "max": null,
        "enum": null,
        "config_key": "solver_calibration_fatol",
        "scope": "scenario"
      }
    ],
    "ports": {
      "inputs": [
        {
          "name": "strategic",
          "accepts": [
            "strategic"
          ],
          "cardinality": "0..n"
        }
      ],
      "outputs": [
        {
          "name": "price_formation",
          "type": "price_formation"
        }
      ]
    },
    "constraints": []
  },
  {
    "id": "forward_transmission",
    "label": "Forward Transmission (λ overlay)",
    "category": "price_formation",
    "doc": "solvers/transmission.py:solve_transmission_path, blend_prices",
    "params": [
      {
        "name": "model_approach",
        "type": "enum",
        "default": "competitive",
        "unit": null,
        "min": null,
        "max": null,
        "enum": [
          "competitive",
          "hotelling",
          "banking",
          "nash_cournot",
          "all"
        ],
        "config_key": "model_approach",
        "scope": "scenario"
      },
      {
        "name": "forward_transmission_lambda",
        "type": "float",
        "default": null,
        "unit": null,
        "min": 0,
        "max": 1,
        "enum": null,
        "config_key": "forward_transmission_lambda",
        "scope": "scenario"
      },
      {
        "name": "solver_competitive_max_iters",
        "type": "int",
        "default": 25,
        "unit": null,
        "min": null,
        "max": null,
        "enum": null,
        "config_key": "solver_competitive_max_iters",
        "scope": "scenario"
      },
      {
        "name": "solver_competitive_tolerance",
        "type": "float",
        "default": 0.001,
        "unit": null,
        "min": null,
        "max": null,
        "enum": null,
        "config_key": "solver_competitive_tolerance",
        "scope": "scenario"
      },
      {
        "name": "solver_hotelling_max_bisection_iters",
        "type": "int",
        "default": 80,
        "unit": null,
        "min": null,
        "max": null,
        "enum": null,
        "config_key": "solver_hotelling_max_bisection_iters",
        "scope": "scenario"
      },
      {
        "name": "solver_hotelling_max_lambda_expansions",
        "type": "int",
        "default": 20,
        "unit": null,
        "min": null,
        "max": null,
        "enum": null,
        "config_key": "solver_hotelling_max_lambda_expansions",
        "scope": "scenario"
      },
      {
        "name": "solver_hotelling_convergence_tol",
        "type": "float",
        "default": 0.0001,
        "unit": null,
        "min": null,
        "max": null,
        "enum": null,
        "config_key": "solver_hotelling_convergence_tol",
        "scope": "scenario"
      },
      {
        "name": "solver_hotelling_lambda_initial_low",
        "type": "float",
        "default": 0.001,
        "unit": null,
        "min": null,
        "max": null,
        "enum": null,
        "config_key": "solver_hotelling_lambda_initial_low",
        "scope": "scenario"
      },
      {
        "name": "solver_hotelling_lambda_initial_high",
        "type": "float",
        "default": 20,
        "unit": null,
        "min": null,
        "max": null,
        "enum": null,
        "config_key": "solver_hotelling_lambda_initial_high",
        "scope": "scenario"
      },
      {
        "name": "solver_hotelling_lambda_expand_factor",
        "type": "float",
        "default": 3,
        "unit": null,
        "min": null,
        "max": null,
        "enum": null,
        "config_key": "solver_hotelling_lambda_expand_factor",
        "scope": "scenario"
      },
      {
        "name": "discount_rate",
        "type": "float",
        "default": 0.04,
        "unit": "1/yr",
        "min": null,
        "max": null,
        "enum": null,
        "config_key": "discount_rate",
        "scope": "scenario"
      },
      {
        "name": "risk_premium",
        "type": "float",
        "default": 0,
        "unit": "1/yr",
        "min": null,
        "max": null,
        "enum": null,
        "config_key": "risk_premium",
        "scope": "scenario"
      },
      {
        "name": "solver_penalty_price_multiplier",
        "type": "float",
        "default": 1.25,
        "unit": null,
        "min": null,
        "max": null,
        "enum": null,
        "config_key": "solver_penalty_price_multiplier",
        "scope": "scenario"
      },
      {
        "name": "solver_price_bracket_expand_factor",
        "type": "float",
        "default": 2,
        "unit": null,
        "min": null,
        "max": null,
        "enum": null,
        "config_key": "solver_price_bracket_expand_factor",
        "scope": "scenario"
      },
      {
        "name": "solver_price_bracket_max_expansions",
        "type": "int",
        "default": 10,
        "unit": null,
        "min": null,
        "max": null,
        "enum": null,
        "config_key": "solver_price_bracket_max_expansions",
        "scope": "scenario"
      },
      {
        "name": "solver_slsqp_max_iters",
        "type": "int",
        "default": 400,
        "unit": null,
        "min": null,
        "max": null,
        "enum": null,
        "config_key": "solver_slsqp_max_iters",
        "scope": "scenario"
      },
      {
        "name": "solver_slsqp_ftol",
        "type": "float",
        "default": 1e-9,
        "unit": null,
        "min": null,
        "max": null,
        "enum": null,
        "config_key": "solver_slsqp_ftol",
        "scope": "scenario"
      },
      {
        "name": "solver_calibration_xatol",
        "type": "float",
        "default": 0.1,
        "unit": null,
        "min": null,
        "max": null,
        "enum": null,
        "config_key": "solver_calibration_xatol",
        "scope": "scenario"
      },
      {
        "name": "solver_calibration_fatol",
        "type": "float",
        "default": 0.01,
        "unit": null,
        "min": null,
        "max": null,
        "enum": null,
        "config_key": "solver_calibration_fatol",
        "scope": "scenario"
      }
    ],
    "ports": {
      "inputs": [],
      "outputs": [
        {
          "name": "price_formation",
          "type": "price_formation"
        }
      ]
    },
    "constraints": []
  },
  {
    "id": "msr_bank_threshold",
    "label": "MSR (bank threshold)",
    "category": "policy",
    "doc": "solvers/msr.py:MSRState.apply",
    "params": [
      {
        "name": "msr_enabled",
        "type": "bool",
        "default": true,
        "unit": null,
        "min": null,
        "max": null,
        "enum": null,
        "config_key": "msr_enabled",
        "scope": "scenario"
      },
      {
        "name": "msr_mode",
        "type": "enum",
        "default": "bank_threshold",
        "unit": null,
        "min": null,
        "max": null,
        "enum": [
          "bank_threshold",
          "price_band",
          "surplus_rule",
          "hybrid"
        ],
        "config_key": "msr_mode",
        "scope": "scenario"
      },
      {
        "name": "msr_upper_threshold",
        "type": "float",
        "default": 200,
        "unit": "Mt CO2e",
        "min": null,
        "max": null,
        "enum": null,
        "config_key": "msr_upper_threshold",
        "scope": "scenario"
      },
      {
        "name": "msr_lower_threshold",
        "type": "float",
        "default": 50,
        "unit": "Mt CO2e",
        "min": null,
        "max": null,
        "enum": null,
        "config_key": "msr_lower_threshold",
        "scope": "scenario"
      },
      {
        "name": "msr_withhold_rate",
        "type": "float",
        "default": 0.12,
        "unit": null,
        "min": 0,
        "max": 1,
        "enum": null,
        "config_key": "msr_withhold_rate",
        "scope": "scenario"
      },
      {
        "name": "msr_release_rate",
        "type": "float",
        "default": 50,
        "unit": "Mt CO2e/yr",
        "min": null,
        "max": null,
        "enum": null,
        "config_key": "msr_release_rate",
        "scope": "scenario"
      },
      {
        "name": "msr_cancel_excess",
        "type": "bool",
        "default": false,
        "unit": null,
        "min": null,
        "max": null,
        "enum": null,
        "config_key": "msr_cancel_excess",
        "scope": "scenario"
      },
      {
        "name": "msr_cancel_threshold",
        "type": "float",
        "default": 400,
        "unit": "Mt CO2e",
        "min": null,
        "max": null,
        "enum": null,
        "config_key": "msr_cancel_threshold",
        "scope": "scenario"
      },
      {
        "name": "msr_initial_reserve_mt",
        "type": "float",
        "default": 0,
        "unit": "Mt CO2e",
        "min": null,
        "max": null,
        "enum": null,
        "config_key": "msr_initial_reserve_mt",
        "scope": "scenario"
      },
      {
        "name": "msr_start_year",
        "type": "float",
        "default": 0,
        "unit": "yr",
        "min": null,
        "max": null,
        "enum": null,
        "config_key": "msr_start_year",
        "scope": "scenario"
      },
      {
        "name": "announced",
        "type": "str",
        "default": "",
        "unit": null,
        "min": null,
        "max": null,
        "enum": null,
        "config_key": "policy_events",
        "scope": "scenario"
      }
    ],
    "ports": {
      "inputs": [],
      "outputs": [
        {
          "name": "policy",
          "type": "policy"
        }
      ]
    },
    "constraints": [
      {
        "kind": "excludes",
        "block": "kmsr_decree"
      }
    ]
  },
  {
    "id": "kmsr_decree",
    "label": "K-MSR Decree",
    "category": "policy",
    "doc": "solvers/banking.py:_decree_msr_action",
    "params": [
      {
        "name": "msr_enabled",
        "type": "bool",
        "default": true,
        "unit": null,
        "min": null,
        "max": null,
        "enum": null,
        "config_key": "msr_enabled",
        "scope": "scenario"
      },
      {
        "name": "msr_mode",
        "type": "enum",
        "default": "hybrid",
        "unit": null,
        "min": null,
        "max": null,
        "enum": [
          "price_band",
          "surplus_rule",
          "hybrid"
        ],
        "config_key": "msr_mode",
        "scope": "scenario"
      },
      {
        "name": "msr_price_band_high",
        "type": "float",
        "default": 25000,
        "unit": null,
        "min": null,
        "max": null,
        "enum": null,
        "config_key": "msr_price_band_high",
        "scope": "scenario"
      },
      {
        "name": "msr_price_band_low",
        "type": "float",
        "default": 15000,
        "unit": null,
        "min": null,
        "max": null,
        "enum": null,
        "config_key": "msr_price_band_low",
        "scope": "scenario"
      },
      {
        "name": "msr_surplus_upper_ratio",
        "type": "float",
        "default": 0.18,
        "unit": null,
        "min": 0,
        "max": 1,
        "enum": null,
        "config_key": "msr_surplus_upper_ratio",
        "scope": "scenario"
      },
      {
        "name": "msr_surplus_lower_ratio",
        "type": "float",
        "default": 0.05,
        "unit": null,
        "min": 0,
        "max": 1,
        "enum": null,
        "config_key": "msr_surplus_lower_ratio",
        "scope": "scenario"
      },
      {
        "name": "msr_max_intake_mt",
        "type": "float",
        "default": 20,
        "unit": "Mt CO2e/yr",
        "min": null,
        "max": null,
        "enum": null,
        "config_key": "msr_max_intake_mt",
        "scope": "scenario"
      },
      {
        "name": "msr_max_release_mt",
        "type": "float",
        "default": 20,
        "unit": "Mt CO2e/yr",
        "min": null,
        "max": null,
        "enum": null,
        "config_key": "msr_max_release_mt",
        "scope": "scenario"
      },
      {
        "name": "msr_initial_reserve_mt",
        "type": "float",
        "default": 0,
        "unit": "Mt CO2e",
        "min": null,
        "max": null,
        "enum": null,
        "config_key": "msr_initial_reserve_mt",
        "scope": "scenario"
      },
      {
        "name": "msr_start_year",
        "type": "float",
        "default": 0,
        "unit": "yr",
        "min": null,
        "max": null,
        "enum": null,
        "config_key": "msr_start_year",
        "scope": "scenario"
      },
      {
        "name": "announced",
        "type": "str",
        "default": "",
        "unit": null,
        "min": null,
        "max": null,
        "enum": null,
        "config_key": "policy_events",
        "scope": "scenario"
      }
    ],
    "ports": {
      "inputs": [],
      "outputs": [
        {
          "name": "policy",
          "type": "policy"
        }
      ]
    },
    "constraints": [
      {
        "kind": "requires",
        "block": "rubin_schennach_banking"
      },
      {
        "kind": "excludes",
        "block": "msr_bank_threshold"
      }
    ]
  },
  {
    "id": "ccr",
    "label": "Carbon Cap Rule (CCR)",
    "category": "policy",
    "doc": "solvers/ccr.py:CCRState.cap_adjustment",
    "params": [
      {
        "name": "ccr_enabled",
        "type": "bool",
        "default": true,
        "unit": null,
        "min": null,
        "max": null,
        "enum": null,
        "config_key": "ccr_enabled",
        "scope": "scenario"
      },
      {
        "name": "ccr_phi_emissions",
        "type": "float",
        "default": 0,
        "unit": null,
        "min": null,
        "max": null,
        "enum": null,
        "config_key": "ccr_phi_emissions",
        "scope": "scenario"
      },
      {
        "name": "ccr_phi_abatement_cost",
        "type": "float",
        "default": 0,
        "unit": null,
        "min": null,
        "max": null,
        "enum": null,
        "config_key": "ccr_phi_abatement_cost",
        "scope": "scenario"
      },
      {
        "name": "ccr_reference_emissions",
        "type": "float",
        "default": 0,
        "unit": "Mt CO2e",
        "min": null,
        "max": null,
        "enum": null,
        "config_key": "ccr_reference_emissions",
        "scope": "scenario"
      },
      {
        "name": "ccr_reference_abatement_cost",
        "type": "float",
        "default": 0,
        "unit": null,
        "min": null,
        "max": null,
        "enum": null,
        "config_key": "ccr_reference_abatement_cost",
        "scope": "scenario"
      },
      {
        "name": "ccr_start_year",
        "type": "float",
        "default": 0,
        "unit": "yr",
        "min": null,
        "max": null,
        "enum": null,
        "config_key": "ccr_start_year",
        "scope": "scenario"
      },
      {
        "name": "announced",
        "type": "str",
        "default": "",
        "unit": null,
        "min": null,
        "max": null,
        "enum": null,
        "config_key": "policy_events",
        "scope": "scenario"
      }
    ],
    "ports": {
      "inputs": [],
      "outputs": [
        {
          "name": "policy",
          "type": "policy"
        }
      ]
    },
    "constraints": [
      {
        "kind": "requires",
        "block": "competitive_clearing"
      }
    ]
  },
  {
    "id": "price_floor",
    "label": "Price Floor",
    "category": "policy",
    "doc": "bound clamping in market/equilibrium.py",
    "params": [
      {
        "name": "price_lower_bound",
        "type": "float",
        "default": 0,
        "unit": "currency/tCO2e",
        "min": null,
        "max": null,
        "enum": null,
        "config_key": "price_lower_bound",
        "scope": "year"
      },
      {
        "name": "price_floor_trajectory",
        "type": "dict",
        "default": {},
        "unit": null,
        "min": null,
        "max": null,
        "enum": null,
        "config_key": "price_floor_trajectory",
        "scope": "scenario"
      },
      {
        "name": "announced",
        "type": "str",
        "default": "",
        "unit": null,
        "min": null,
        "max": null,
        "enum": null,
        "config_key": "policy_events",
        "scope": "scenario"
      }
    ],
    "ports": {
      "inputs": [],
      "outputs": [
        {
          "name": "policy",
          "type": "policy"
        }
      ]
    },
    "constraints": []
  },
  {
    "id": "price_ceiling",
    "label": "Price Ceiling",
    "category": "policy",
    "doc": "bound clamping in market/equilibrium.py",
    "params": [
      {
        "name": "price_upper_bound",
        "type": "float",
        "default": 100,
        "unit": "currency/tCO2e",
        "min": null,
        "max": null,
        "enum": null,
        "config_key": "price_upper_bound",
        "scope": "year"
      },
      {
        "name": "price_ceiling_trajectory",
        "type": "dict",
        "default": {},
        "unit": null,
        "min": null,
        "max": null,
        "enum": null,
        "config_key": "price_ceiling_trajectory",
        "scope": "scenario"
      },
      {
        "name": "announced",
        "type": "str",
        "default": "",
        "unit": null,
        "min": null,
        "max": null,
        "enum": null,
        "config_key": "policy_events",
        "scope": "scenario"
      }
    ],
    "ports": {
      "inputs": [],
      "outputs": [
        {
          "name": "policy",
          "type": "policy"
        }
      ]
    },
    "constraints": []
  },
  {
    "id": "auction_reserve",
    "label": "Auction Reserve",
    "category": "policy",
    "doc": "auction mechanics in market/equilibrium.py:solve_equilibrium",
    "params": [
      {
        "name": "auction_reserve_price",
        "type": "float",
        "default": 0,
        "unit": "currency/tCO2e",
        "min": null,
        "max": null,
        "enum": null,
        "config_key": "auction_reserve_price",
        "scope": "year"
      },
      {
        "name": "minimum_bid_coverage",
        "type": "float",
        "default": 0,
        "unit": null,
        "min": 0,
        "max": 1,
        "enum": null,
        "config_key": "minimum_bid_coverage",
        "scope": "year"
      },
      {
        "name": "unsold_treatment",
        "type": "enum",
        "default": "reserve",
        "unit": null,
        "min": null,
        "max": null,
        "enum": [
          "reserve",
          "cancel",
          "carry_forward"
        ],
        "config_key": "unsold_treatment",
        "scope": "year"
      },
      {
        "name": "announced",
        "type": "str",
        "default": "",
        "unit": null,
        "min": null,
        "max": null,
        "enum": null,
        "config_key": "policy_events",
        "scope": "scenario"
      }
    ],
    "ports": {
      "inputs": [],
      "outputs": [
        {
          "name": "policy",
          "type": "policy"
        }
      ]
    },
    "constraints": []
  },
  {
    "id": "cancellation",
    "label": "Cancellation Schedule",
    "category": "policy",
    "doc": "year-level cap removal",
    "params": [
      {
        "name": "cancelled_allowances",
        "type": "float",
        "default": 0,
        "unit": "Mt CO2e",
        "min": null,
        "max": null,
        "enum": null,
        "config_key": "cancelled_allowances",
        "scope": "year"
      },
      {
        "name": "announced",
        "type": "str",
        "default": "",
        "unit": null,
        "min": null,
        "max": null,
        "enum": null,
        "config_key": "policy_events",
        "scope": "scenario"
      }
    ],
    "ports": {
      "inputs": [],
      "outputs": [
        {
          "name": "policy",
          "type": "policy"
        }
      ]
    },
    "constraints": []
  },
  {
    "id": "cap_path",
    "label": "Cap Trajectory",
    "category": "policy",
    "doc": "config_io/builder.py:_interp_value",
    "params": [
      {
        "name": "cap_trajectory",
        "type": "dict",
        "default": {},
        "unit": null,
        "min": null,
        "max": null,
        "enum": null,
        "config_key": "cap_trajectory",
        "scope": "scenario"
      },
      {
        "name": "announced",
        "type": "str",
        "default": "",
        "unit": null,
        "min": null,
        "max": null,
        "enum": null,
        "config_key": "policy_events",
        "scope": "scenario"
      }
    ],
    "ports": {
      "inputs": [],
      "outputs": [
        {
          "name": "policy",
          "type": "policy"
        }
      ]
    },
    "constraints": []
  },
  {
    "id": "free_allocation_phaseout",
    "label": "Free-Allocation Phase-Out",
    "category": "policy",
    "doc": "config_io/builder.py:_interp_ratio",
    "params": [
      {
        "name": "free_allocation_trajectories",
        "type": "list",
        "default": [],
        "unit": null,
        "min": null,
        "max": null,
        "enum": null,
        "config_key": "free_allocation_trajectories",
        "scope": "scenario"
      },
      {
        "name": "announced",
        "type": "str",
        "default": "",
        "unit": null,
        "min": null,
        "max": null,
        "enum": null,
        "config_key": "policy_events",
        "scope": "scenario"
      }
    ],
    "ports": {
      "inputs": [],
      "outputs": [
        {
          "name": "policy",
          "type": "policy"
        }
      ]
    },
    "constraints": []
  },
  {
    "id": "oba",
    "label": "Output-Based Allocation",
    "category": "policy",
    "doc": "OBA override in config_io/builder.py:build_market_from_year — no owned params: production_output/benchmark_emission_intensity already live on the participant block.",
    "params": [
      {
        "name": "announced",
        "type": "str",
        "default": "",
        "unit": null,
        "min": null,
        "max": null,
        "enum": null,
        "config_key": "policy_events",
        "scope": "scenario"
      }
    ],
    "ports": {
      "inputs": [],
      "outputs": [
        {
          "name": "policy",
          "type": "policy"
        }
      ]
    },
    "constraints": []
  },
  {
    "id": "cbam",
    "label": "CBAM",
    "category": "policy",
    "doc": "CBAM liability in market/results.py (diagnostics-only, F6)",
    "params": [
      {
        "name": "eua_price",
        "type": "float",
        "default": 0,
        "unit": "currency/tCO2e",
        "min": null,
        "max": null,
        "enum": null,
        "config_key": "eua_price",
        "scope": "year"
      },
      {
        "name": "eua_prices",
        "type": "dict",
        "default": {},
        "unit": null,
        "min": null,
        "max": null,
        "enum": null,
        "config_key": "eua_prices",
        "scope": "year"
      },
      {
        "name": "eua_price_ensemble",
        "type": "dict",
        "default": {},
        "unit": null,
        "min": null,
        "max": null,
        "enum": null,
        "config_key": "eua_price_ensemble",
        "scope": "year"
      },
      {
        "name": "announced",
        "type": "str",
        "default": "",
        "unit": null,
        "min": null,
        "max": null,
        "enum": null,
        "config_key": "policy_events",
        "scope": "scenario"
      }
    ],
    "ports": {
      "inputs": [],
      "outputs": [
        {
          "name": "policy",
          "type": "policy"
        }
      ]
    },
    "constraints": []
  },
  {
    "id": "hoarding",
    "label": "Hoarding Inflow",
    "category": "policy",
    "doc": "solvers/banking.py:_hoarding_inflow",
    "params": [
      {
        "name": "hoarding_inflow",
        "type": "float",
        "default": 0,
        "unit": "Mt CO2e",
        "min": null,
        "max": null,
        "enum": null,
        "config_key": "hoarding_inflow",
        "scope": "year"
      },
      {
        "name": "announced",
        "type": "str",
        "default": "",
        "unit": null,
        "min": null,
        "max": null,
        "enum": null,
        "config_key": "policy_events",
        "scope": "scenario"
      }
    ],
    "ports": {
      "inputs": [],
      "outputs": [
        {
          "name": "policy",
          "type": "policy"
        }
      ]
    },
    "constraints": [
      {
        "kind": "requires",
        "block": "rubin_schennach_banking"
      }
    ]
  },
  {
    "id": "expectations",
    "label": "Expectations Rule",
    "category": "expectations",
    "doc": "solvers/expectations.py:ExpectationSpec, derive_expected_prices",
    "params": [
      {
        "name": "expectation_rule",
        "type": "enum",
        "default": "next_year_baseline",
        "unit": null,
        "min": null,
        "max": null,
        "enum": [
          "myopic",
          "next_year_baseline",
          "perfect_foresight",
          "manual"
        ],
        "config_key": "expectation_rule",
        "scope": "year"
      },
      {
        "name": "manual_expected_price",
        "type": "float",
        "default": 0,
        "unit": "currency/tCO2e",
        "min": null,
        "max": null,
        "enum": null,
        "config_key": "manual_expected_price",
        "scope": "year"
      }
    ],
    "ports": {
      "inputs": [],
      "outputs": [
        {
          "name": "expectations",
          "type": "expectations"
        }
      ]
    },
    "constraints": []
  },
  {
    "id": "price_elastic_baseline",
    "label": "Price-Elastic Baseline (Option A)",
    "category": "expectations",
    "doc": "participant/models.py:MarketParticipant.activity_multiplier",
    "params": [
      {
        "name": "reference_carbon_price",
        "type": "float",
        "default": 0,
        "unit": "currency/tCO2e",
        "min": null,
        "max": null,
        "enum": null,
        "config_key": "reference_carbon_price",
        "scope": "scenario"
      }
    ],
    "ports": {
      "inputs": [],
      "outputs": [
        {
          "name": "baseline",
          "type": "baseline"
        }
      ]
    },
    "constraints": []
  },
  {
    "id": "participant",
    "label": "Participant",
    "category": "participants",
    "doc": "participant/models.py:MarketParticipant via build_participant",
    "params": [
      {
        "name": "name",
        "type": "str",
        "default": "New Participant",
        "unit": null,
        "min": null,
        "max": null,
        "enum": null,
        "config_key": "name",
        "scope": "participant"
      },
      {
        "name": "sector_group",
        "type": "str",
        "default": "",
        "unit": null,
        "min": null,
        "max": null,
        "enum": null,
        "config_key": "sector_group",
        "scope": "participant"
      },
      {
        "name": "initial_emissions",
        "type": "float",
        "default": 0,
        "unit": "Mt CO2e",
        "min": null,
        "max": null,
        "enum": null,
        "config_key": "initial_emissions",
        "scope": "participant"
      },
      {
        "name": "initial_emissions_trajectory",
        "type": "dict",
        "default": {},
        "unit": null,
        "min": null,
        "max": null,
        "enum": null,
        "config_key": "initial_emissions_trajectory",
        "scope": "participant"
      },
      {
        "name": "free_allocation_ratio",
        "type": "float",
        "default": 0,
        "unit": null,
        "min": 0,
        "max": 1,
        "enum": null,
        "config_key": "free_allocation_ratio",
        "scope": "participant"
      },
      {
        "name": "penalty_price",
        "type": "float",
        "default": 0,
        "unit": "currency/tCO2e",
        "min": null,
        "max": null,
        "enum": null,
        "config_key": "penalty_price",
        "scope": "participant"
      },
      {
        "name": "abatement_type",
        "type": "enum",
        "default": "linear",
        "unit": null,
        "min": null,
        "max": null,
        "enum": [
          "linear",
          "threshold",
          "piecewise"
        ],
        "config_key": "abatement_type",
        "scope": "participant"
      },
      {
        "name": "max_abatement",
        "type": "float",
        "default": 0,
        "unit": "Mt CO2e",
        "min": null,
        "max": null,
        "enum": null,
        "config_key": "max_abatement",
        "scope": "participant"
      },
      {
        "name": "cost_slope",
        "type": "float",
        "default": 1,
        "unit": null,
        "min": null,
        "max": null,
        "enum": null,
        "config_key": "cost_slope",
        "scope": "participant"
      },
      {
        "name": "threshold_cost",
        "type": "float",
        "default": 0,
        "unit": null,
        "min": null,
        "max": null,
        "enum": null,
        "config_key": "threshold_cost",
        "scope": "participant"
      },
      {
        "name": "mac_blocks",
        "type": "list",
        "default": [],
        "unit": null,
        "min": null,
        "max": null,
        "enum": null,
        "config_key": "mac_blocks",
        "scope": "participant"
      },
      {
        "name": "technology_options",
        "type": "list",
        "default": [],
        "unit": null,
        "min": null,
        "max": null,
        "enum": null,
        "config_key": "technology_options",
        "scope": "participant"
      },
      {
        "name": "sector_allocation_share",
        "type": "float",
        "default": 0,
        "unit": null,
        "min": 0,
        "max": 1,
        "enum": null,
        "config_key": "sector_allocation_share",
        "scope": "participant"
      },
      {
        "name": "production_output",
        "type": "float",
        "default": 0,
        "unit": null,
        "min": null,
        "max": null,
        "enum": null,
        "config_key": "production_output",
        "scope": "participant"
      },
      {
        "name": "benchmark_emission_intensity",
        "type": "float",
        "default": 0,
        "unit": null,
        "min": null,
        "max": null,
        "enum": null,
        "config_key": "benchmark_emission_intensity",
        "scope": "participant"
      },
      {
        "name": "output_price_elasticity",
        "type": "float",
        "default": 0,
        "unit": null,
        "min": null,
        "max": null,
        "enum": null,
        "config_key": "output_price_elasticity",
        "scope": "participant"
      },
      {
        "name": "electricity_consumption",
        "type": "float",
        "default": 0,
        "unit": "MWh",
        "min": null,
        "max": null,
        "enum": null,
        "config_key": "electricity_consumption",
        "scope": "participant"
      },
      {
        "name": "grid_emission_factor",
        "type": "float",
        "default": 0,
        "unit": "tCO2/MWh",
        "min": null,
        "max": null,
        "enum": null,
        "config_key": "grid_emission_factor",
        "scope": "participant"
      },
      {
        "name": "grid_emission_factor_trajectory",
        "type": "dict",
        "default": {},
        "unit": null,
        "min": null,
        "max": null,
        "enum": null,
        "config_key": "grid_emission_factor_trajectory",
        "scope": "participant"
      },
      {
        "name": "scope2_cbam_coverage",
        "type": "float",
        "default": 0,
        "unit": null,
        "min": 0,
        "max": 1,
        "enum": null,
        "config_key": "scope2_cbam_coverage",
        "scope": "participant"
      },
      {
        "name": "cbam_export_share",
        "type": "float",
        "default": 0,
        "unit": null,
        "min": 0,
        "max": 1,
        "enum": null,
        "config_key": "cbam_export_share",
        "scope": "participant"
      },
      {
        "name": "cbam_coverage_ratio",
        "type": "float",
        "default": 1,
        "unit": null,
        "min": 0,
        "max": 1,
        "enum": null,
        "config_key": "cbam_coverage_ratio",
        "scope": "participant"
      },
      {
        "name": "cbam_jurisdictions",
        "type": "list",
        "default": [],
        "unit": null,
        "min": null,
        "max": null,
        "enum": null,
        "config_key": "cbam_jurisdictions",
        "scope": "participant"
      }
    ],
    "ports": {
      "inputs": [
        {
          "name": "options",
          "accepts": [
            "technology_option"
          ],
          "cardinality": "0..n"
        }
      ],
      "outputs": [
        {
          "name": "compliance",
          "type": "compliance"
        },
        {
          "name": "member_of",
          "type": "member_of"
        },
        {
          "name": "strategic",
          "type": "strategic"
        }
      ]
    },
    "constraints": []
  },
  {
    "id": "technology_option",
    "label": "Technology Option",
    "category": "participants",
    "doc": "participant/models.py:TechnologyOption via build_technology_option",
    "params": [
      {
        "name": "name",
        "type": "str",
        "default": "New Technology",
        "unit": null,
        "min": null,
        "max": null,
        "enum": null,
        "config_key": "name",
        "scope": "participant"
      },
      {
        "name": "initial_emissions",
        "type": "float",
        "default": 0,
        "unit": "Mt CO2e",
        "min": null,
        "max": null,
        "enum": null,
        "config_key": "initial_emissions",
        "scope": "participant"
      },
      {
        "name": "free_allocation_ratio",
        "type": "float",
        "default": 0,
        "unit": null,
        "min": 0,
        "max": 1,
        "enum": null,
        "config_key": "free_allocation_ratio",
        "scope": "participant"
      },
      {
        "name": "penalty_price",
        "type": "float",
        "default": 0,
        "unit": null,
        "min": null,
        "max": null,
        "enum": null,
        "config_key": "penalty_price",
        "scope": "participant"
      },
      {
        "name": "abatement_type",
        "type": "enum",
        "default": "linear",
        "unit": null,
        "min": null,
        "max": null,
        "enum": [
          "linear",
          "threshold",
          "piecewise"
        ],
        "config_key": "abatement_type",
        "scope": "participant"
      },
      {
        "name": "max_abatement",
        "type": "float",
        "default": 0,
        "unit": null,
        "min": null,
        "max": null,
        "enum": null,
        "config_key": "max_abatement",
        "scope": "participant"
      },
      {
        "name": "cost_slope",
        "type": "float",
        "default": 1,
        "unit": null,
        "min": null,
        "max": null,
        "enum": null,
        "config_key": "cost_slope",
        "scope": "participant"
      },
      {
        "name": "threshold_cost",
        "type": "float",
        "default": 0,
        "unit": null,
        "min": null,
        "max": null,
        "enum": null,
        "config_key": "threshold_cost",
        "scope": "participant"
      },
      {
        "name": "mac_blocks",
        "type": "list",
        "default": [],
        "unit": null,
        "min": null,
        "max": null,
        "enum": null,
        "config_key": "mac_blocks",
        "scope": "participant"
      },
      {
        "name": "fixed_cost",
        "type": "float",
        "default": 0,
        "unit": null,
        "min": null,
        "max": null,
        "enum": null,
        "config_key": "fixed_cost",
        "scope": "participant"
      },
      {
        "name": "max_activity_share",
        "type": "float",
        "default": 1,
        "unit": null,
        "min": 0,
        "max": 1,
        "enum": null,
        "config_key": "max_activity_share",
        "scope": "participant"
      }
    ],
    "ports": {
      "inputs": [],
      "outputs": [
        {
          "name": "option",
          "type": "technology_option"
        }
      ]
    },
    "constraints": []
  },
  {
    "id": "sector",
    "label": "Sector",
    "category": "participants",
    "doc": "sector pool derivation in config_io/builder.py:build_market_from_year",
    "params": [
      {
        "name": "sector_name",
        "type": "str",
        "default": "New Sector",
        "unit": null,
        "min": null,
        "max": null,
        "enum": null,
        "config_key": "sectors",
        "scope": "scenario"
      },
      {
        "name": "cap_trajectory",
        "type": "dict",
        "default": null,
        "unit": null,
        "min": null,
        "max": null,
        "enum": null,
        "config_key": "sectors",
        "scope": "scenario"
      },
      {
        "name": "auction_share_trajectory",
        "type": "dict",
        "default": null,
        "unit": null,
        "min": null,
        "max": null,
        "enum": null,
        "config_key": "sectors",
        "scope": "scenario"
      },
      {
        "name": "carbon_budget",
        "type": "float",
        "default": 0,
        "unit": "Mt CO2e",
        "min": null,
        "max": null,
        "enum": null,
        "config_key": "sectors",
        "scope": "scenario"
      }
    ],
    "ports": {
      "inputs": [
        {
          "name": "members",
          "accepts": [
            "member_of"
          ],
          "cardinality": "0..n"
        }
      ],
      "outputs": [
        {
          "name": "pool",
          "type": "sector_pool"
        }
      ]
    },
    "constraints": []
  },
  {
    "id": "batch_sweep",
    "label": "Batch Sweep",
    "category": "analysis",
    "doc": "analysis/batch.py:run_batch",
    "params": [
      {
        "name": "sweeps",
        "type": "list",
        "default": [],
        "unit": null,
        "min": null,
        "max": null,
        "enum": null,
        "config_key": "sweeps",
        "scope": "edge"
      }
    ],
    "ports": {
      "inputs": [
        {
          "name": "results",
          "accepts": [
            "results"
          ],
          "cardinality": "1"
        }
      ],
      "outputs": []
    },
    "constraints": []
  },
  {
    "id": "calibration",
    "label": "Calibration",
    "category": "analysis",
    "doc": "analysis/calibration.py:calibrate_slopes",
    "params": [
      {
        "name": "observed_prices",
        "type": "dict",
        "default": null,
        "unit": null,
        "min": null,
        "max": null,
        "enum": null,
        "config_key": "observed_prices",
        "scope": "edge"
      },
      {
        "name": "participant_names",
        "type": "list",
        "default": [],
        "unit": null,
        "min": null,
        "max": null,
        "enum": null,
        "config_key": "participant_names",
        "scope": "edge"
      },
      {
        "name": "initial_slopes",
        "type": "dict",
        "default": null,
        "unit": null,
        "min": null,
        "max": null,
        "enum": null,
        "config_key": "initial_slopes",
        "scope": "edge"
      },
      {
        "name": "max_iter",
        "type": "int",
        "default": 200,
        "unit": null,
        "min": null,
        "max": null,
        "enum": null,
        "config_key": "max_iter",
        "scope": "edge"
      }
    ],
    "ports": {
      "inputs": [
        {
          "name": "results",
          "accepts": [
            "results"
          ],
          "cardinality": "1"
        }
      ],
      "outputs": []
    },
    "constraints": []
  },
  {
    "id": "narrative",
    "label": "Narrative",
    "category": "analysis",
    "doc": "analysis/narrative.py:generate_narrative",
    "params": [
      {
        "name": "scenario_name",
        "type": "str",
        "default": "",
        "unit": null,
        "min": null,
        "max": null,
        "enum": null,
        "config_key": "scenario_name",
        "scope": "edge"
      }
    ],
    "ports": {
      "inputs": [
        {
          "name": "results",
          "accepts": [
            "results"
          ],
          "cardinality": "1"
        }
      ],
      "outputs": []
    },
    "constraints": []
  },
  {
    "id": "investment_trigger",
    "label": "Investment Trigger",
    "category": "analysis",
    "doc": "analysis/investment_trigger.py",
    "params": [
      {
        "name": "sigma",
        "type": "float",
        "default": 0.2,
        "unit": null,
        "min": null,
        "max": null,
        "enum": null,
        "config_key": "sigma",
        "scope": "edge"
      },
      {
        "name": "r",
        "type": "float",
        "default": 0.04,
        "unit": null,
        "min": null,
        "max": null,
        "enum": null,
        "config_key": "r",
        "scope": "edge"
      },
      {
        "name": "y",
        "type": "float",
        "default": 1,
        "unit": null,
        "min": null,
        "max": null,
        "enum": null,
        "config_key": "y",
        "scope": "edge"
      },
      {
        "name": "credibility",
        "type": "float",
        "default": 1,
        "unit": null,
        "min": 0,
        "max": 1,
        "enum": null,
        "config_key": "credibility",
        "scope": "edge"
      }
    ],
    "ports": {
      "inputs": [
        {
          "name": "results",
          "accepts": [
            "results"
          ],
          "cardinality": "1"
        }
      ],
      "outputs": []
    },
    "constraints": []
  },
  {
    "id": "external_feedback",
    "label": "External Feedback Loop",
    "category": "analysis",
    "doc": "coupling/loop.py:run_coupled_simulation + coupling/adapters.py",
    "params": [
      {
        "name": "adapter",
        "type": "str",
        "default": "",
        "unit": null,
        "min": null,
        "max": null,
        "enum": null,
        "config_key": "adapter",
        "scope": "edge"
      },
      {
        "name": "elasticity",
        "type": "float",
        "default": 0,
        "unit": null,
        "min": null,
        "max": null,
        "enum": null,
        "config_key": "elasticity",
        "scope": "edge"
      },
      {
        "name": "reference_price",
        "type": "float",
        "default": 0,
        "unit": null,
        "min": null,
        "max": null,
        "enum": null,
        "config_key": "reference_price",
        "scope": "edge"
      },
      {
        "name": "relaxation_weight",
        "type": "float",
        "default": 0.5,
        "unit": null,
        "min": 0,
        "max": 1,
        "enum": null,
        "config_key": "relaxation_weight",
        "scope": "edge"
      },
      {
        "name": "tolerance",
        "type": "float",
        "default": 0.001,
        "unit": null,
        "min": null,
        "max": null,
        "enum": null,
        "config_key": "tolerance",
        "scope": "edge"
      },
      {
        "name": "max_iterations",
        "type": "int",
        "default": 25,
        "unit": null,
        "min": null,
        "max": null,
        "enum": null,
        "config_key": "max_iterations",
        "scope": "edge"
      }
    ],
    "ports": {
      "inputs": [
        {
          "name": "results",
          "accepts": [
            "results"
          ],
          "cardinality": "1"
        }
      ],
      "outputs": []
    },
    "constraints": []
  }
];

export { BLOCKS_FIXTURE };
