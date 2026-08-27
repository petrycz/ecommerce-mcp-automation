from datetime import date
from decimal import Decimal

from openpyxl import load_workbook

from ecommerce_mcp.clients.meta_ads_client import AdInsight, AdPerformanceSummary
from ecommerce_mcp.clients.shopify_client import DailyPnL, LineItem, Order
from ecommerce_mcp.reporting.spreadsheet import build_workbook


def _sample_order() -> Order:
    return Order(
        id=1,
        name="#1001",
        created_at="2026-08-25T09:00:00-04:00",
        currency="USD",
        financial_status="paid",
        total_price=Decimal("84.97"),
        subtotal_price=Decimal("79.97"),
        total_tax=Decimal("5.00"),
        total_discounts=Decimal("0.00"),
        line_items=[
            LineItem(
                id=1,
                product_id=1,
                variant_id=1,
                sku="TSHIRT-BLK-M",
                title="Classic Tee - Black",
                quantity=1,
                price=Decimal("24.99"),
            )
        ],
    )


def _sample_insight() -> AdInsight:
    return AdInsight(
        date_start="2026-08-25",
        date_stop="2026-08-25",
        campaign_id="6001",
        campaign_name="Prospecting - Broad US",
        spend=Decimal("52.30"),
        impressions=6200,
        clicks=104,
        reach=5400,
        purchases=3,
        purchase_value=Decimal("89.97"),
    )


def test_build_workbook_has_three_sheets_with_expected_data(tmp_path):
    pnl = DailyPnL(order_count=1, revenue=Decimal("84.97"), cogs=Decimal("8.50"), gross_profit=Decimal("76.47"))
    ad_summary = AdPerformanceSummary(
        spend=Decimal("52.30"),
        impressions=6200,
        clicks=104,
        purchases=3,
        purchase_value=Decimal("89.97"),
        roas=Decimal("89.97") / Decimal("52.30"),
    )

    wb = build_workbook(
        report_date=date(2026, 8, 25),
        pnl=pnl,
        orders=[_sample_order()],
        ad_summary=ad_summary,
        insights=[_sample_insight()],
    )

    assert wb.sheetnames == ["Summary", "Orders", "Ad Performance"]

    out_file = tmp_path / "report.xlsx"
    wb.save(out_file)
    reloaded = load_workbook(out_file)

    summary = reloaded["Summary"]
    assert summary["A1"].value == "Daily P&L + Ad Performance — 2026-08-25"
    assert summary["B4"].value == 84.97  # Revenue
    assert summary["B6"].value == 76.47  # Gross Profit

    orders_sheet = reloaded["Orders"]
    assert orders_sheet["A1"].value == "Order"
    assert orders_sheet["A2"].value == "#1001"

    ads_sheet = reloaded["Ad Performance"]
    assert ads_sheet["A1"].value == "Date"
    assert ads_sheet["B2"].value == "Prospecting - Broad US"
