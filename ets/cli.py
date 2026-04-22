from __future__ import annotations

import argparse

import pandas as pd

from .config import OUTPUT_DIR
from .scenarios import blank_config, save_config
from .simulation import run_simulation_from_file


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the ETS equilibrium simulator.")
    parser.add_argument(
        "--config",
        type=str,
        help="Path to a JSON config file defining scenarios, years, and participants.",
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default=None,
        help="Directory where CSV outputs and charts will be written.",
    )
    parser.add_argument(
        "--gui",
        action="store_true",
        help="Launch the local browser-based scenario editor.",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8765,
        help="Port for the local browser-based editor.",
    )
    parser.add_argument(
        "--no-browser",
        action="store_true",
        help="Start the local editor without opening a browser automatically.",
    )
    parser.add_argument(
        "--export-template",
        type=str,
        help="Write a blank scenario JSON template to the given path and exit.",
    )
    args = parser.parse_args()

    if args.export_template:
        save_config(blank_config(), args.export_template)
        print(f"Blank config template written to {args.export_template}")
        return

    if args.gui or not args.config:
        from .webapp import launch_web_app

        launch_web_app(port=args.port, open_browser=not args.no_browser)
        return

    pd.set_option("display.float_format", lambda value: f"{value:,.2f}")
    summary_df, participant_df = run_simulation_from_file(
        args.config,
        output_dir=args.output_dir or OUTPUT_DIR,
    )

    print("\nETS Scenario Summary\n")
    print(summary_df.to_string(index=False))

    print("\nParticipant-Level Results\n")
    print(participant_df.to_string(index=False))

    print(f"\nArtifacts written to {args.output_dir or OUTPUT_DIR}")
