"""
OURE CLI - Report Command
=========================
"""

import json

import click
from fpdf import FPDF
from fpdf.enums import XPos, YPos

from .main import cli
from .utils import UI


class RiskReportPDF(FPDF):  # type: ignore
    def header(self) -> None:
        self.set_font("helvetica", "B", 15)
        self.cell(
            0,
            10,
            "OURE - Orbital Conjunction Risk Report",
            border=0,
            new_x=XPos.LMARGIN,
            new_y=YPos.NEXT,
            align="C",
        )
        self.ln(10)

    def footer(self) -> None:
        self.set_y(-15)
        self.set_font("helvetica", "I", 8)
        self.cell(0, 10, f"Page {self.page_no()}", align="C")


@cli.command()
@click.option(
    "--results-file",
    type=click.Path(exists=True),
    required=True,
    help="JSON file from analyze command.",
)
@click.option(
    "--format",
    type=click.Choice(["txt", "json", "csv", "pdf"]),
    default="pdf",
    help="Output format.",
)
@click.option("--output", type=click.Path(), required=True, help="Output file path.")
def report(results_file: str, format: str, output: str) -> None:
    """
    Generate a summary of all high-risk events.
    """
    UI.header("Report Generator", f"Compiling results from {results_file}")

    try:
        with open(results_file) as f:
            data = json.load(f)
    except Exception as e:
        UI.error(f"Failed to read results file: {e}")
        return

    if not data:
        UI.error("No results found in the input file.")
        return

    high_risk_events = [
        event for event in data if event.get("warning_level") in ("RED", "YELLOW")
    ]
    high_risk_events.sort(key=lambda x: float(x.get("pc", 0)), reverse=True)

    if format == "pdf":
        pdf = RiskReportPDF()
        pdf.add_page()
        pdf.set_font("helvetica", size=12)

        pdf.cell(
            0,
            10,
            f"Total Events Analyzed: {len(data)}",
            new_x=XPos.LMARGIN,
            new_y=YPos.NEXT,
        )
        pdf.cell(
            0,
            10,
            f"High-Risk Events (RED/YELLOW): {len(high_risk_events)}",
            new_x=XPos.LMARGIN,
            new_y=YPos.NEXT,
        )
        pdf.ln(10)

        for idx, event in enumerate(high_risk_events, 1):
            pdf.set_font("helvetica", "B", 12)
            pdf.cell(
                0,
                8,
                f"Event #{idx}: {event['primary_id']} vs {event['secondary_id']}",
                new_x=XPos.LMARGIN,
                new_y=YPos.NEXT,
            )
            pdf.set_font("helvetica", size=10)
            pdf.cell(
                0,
                6,
                f"Time of Closest Approach (TCA): {event['tca']}",
                new_x=XPos.LMARGIN,
                new_y=YPos.NEXT,
            )
            pdf.cell(
                0,
                6,
                f"Probability of Collision (Pc): {float(event['pc']):.2e}",
                new_x=XPos.LMARGIN,
                new_y=YPos.NEXT,
            )
            pdf.cell(
                0,
                6,
                f"Warning Level: {event['warning_level']}",
                new_x=XPos.LMARGIN,
                new_y=YPos.NEXT,
            )
            pdf.cell(
                0,
                6,
                f"Miss Distance: {float(event['miss_distance_km']):.3f} km",
                new_x=XPos.LMARGIN,
                new_y=YPos.NEXT,
            )
            pdf.cell(
                0,
                6,
                f"Relative Velocity: {float(event['rel_velocity_km_s']):.2f} km/s",
                new_x=XPos.LMARGIN,
                new_y=YPos.NEXT,
            )
            pdf.ln(5)

        pdf.output(output)
        UI.success(f"PDF report generated successfully: {output}")
    else:
        UI.error(f"Format '{format}' is not yet fully implemented.")
