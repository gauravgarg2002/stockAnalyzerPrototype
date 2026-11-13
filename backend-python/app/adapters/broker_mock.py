"""Mock broker: instant connect; portfolio from sample_user.json + sample prices."""
from __future__ import annotations

from datetime import date

from .. import errors, sources
from . import sample_store as ss
from .base import BrokerPortfolio, PricePoint
from .broker_extras import build_activity, map_quote, unavailable_quote

LABEL = "Your Zerodha account (sample)"


class MockBroker:
    mode = "mock"

    def __init__(self) -> None:
        self.connected = False

    def login_start(self) -> dict:
        self.connected = True
        return {"sampleData": True, "brokerMode": "mock", "status": "CONNECTED", "loginUrl": None, "message": "Sample account connected."}

    def login_status(self) -> dict:
        if self.connected:
            return {"sampleData": True, "brokerMode": "mock", "status": "CONNECTED", "accountLabel": LABEL, "message": "Connected."}
        return {"sampleData": True, "brokerMode": "mock", "status": "NOT_CONNECTED", "accountLabel": None, "message": "Not connected."}

    def login_complete(self, request_token: str) -> dict:
        raise errors.bad_request("Login completion is only used with kite_connect mode.")

    def logout(self) -> dict:
        self.connected = False
        return {"sampleData": True, "brokerMode": "mock", "status": "NOT_CONNECTED", "loginUrl": None,
                "message": "Disconnected. Imported holdings are kept."}

    def portfolio(self) -> BrokerPortfolio:
        if not self.connected:
            raise errors.broker_not_connected("Connect your Zerodha account first.")
        u = ss.sample_user()
        stocks, funds = [], []
        for s in u["stocks"]:
            ps = ss.stock_prices(s["symbol"])
            stocks.append({"symbol": s["symbol"], "isin": ss.stock_records()[s["symbol"]]["isin"], "quantity": s["quantity"], "avgPrice": s["avgPrice"],
                           "lastPrice": ps.points[-1][1] if ps else None, "firstBuyDate": s["firstBuyDate"]})
        for f in u["funds"]:
            ns = ss.navs(f["schemeCode"])
            rec = ss.fund_records()[f["schemeCode"]]
            funds.append({"schemeCode": f["schemeCode"], "isin": rec["isin"], "name": rec["name"], "units": f["units"], "avgNav": f["avgNav"],
                          "lastNav": ns.points[-1][1] if ns else None, "firstBuyDate": f["firstBuyDate"]})
        return BrokerPortfolio(source=sources.ZERODHA, asOf=ss.as_of(), accountLabel=LABEL, stocks=stocks, funds=funds,
                               idleCashInr=u["idleCashInr"], unmatched=[], sampleData=True)

    def historical(self, symbol: str, start: date, end: date) -> list[PricePoint]:
        ps = ss.stock_prices(symbol)
        return [p for p in ps.points if start <= p[0] <= end] if ps else []


    # -- extras: built from the sample price series so the screens can be tried without an account
    def quote(self, symbol: str) -> dict:
        sym = symbol.strip().upper()
        ps = ss.stock_prices(sym)
        if not ps or len(ps.points) < 2:
            return unavailable_quote(sym, "No sample price for this symbol.", True)
        prev, last, d1 = ps.points[-2][1], ps.points[-1][1], ps.points[-1][0]
        lo, hi = min(prev, last) * 0.993, max(prev, last) * 1.006
        row = {"last_price": last, "ohlc": {"open": round(prev * 1.002, 2), "high": round(hi, 2), "low": round(lo, 2), "close": prev},
               "volume": 1_250_000, "timestamp": f"{d1.isoformat()} 15:29:59"}
        return map_quote(row, sym, "NSE (sample)", True)

    def activity(self) -> dict:
        if not self.connected:
            return build_activity(sample=True, connected=False, source=LABEL, as_of=ss.as_of(), positions=None,
                                  orders=None, trades=None, gtts=None)
        u = ss.sample_user()
        held = [s["symbol"] for s in u["stocks"]]

        def last(sym: str) -> float | None:
            ps = ss.stock_prices(sym)
            return ps.points[-1][1] if ps else None

        from ..formatting import format_inr, format_price
        positions = []
        if held:
            sym, lp = held[0], last(held[0])
            if lp:
                avg = round(lp * 0.992, 2)
                positions.append({"symbol": sym, "exchange": "NSE", "product": "MIS", "quantity": 5.0, "avgPrice": avg,
                                  "avgPriceDisplay": format_price(avg), "lastPrice": lp, "lastPriceDisplay": format_price(lp),
                                  "pnl": round((lp - avg) * 5, 2), "pnlDisplay": format_inr(round((lp - avg) * 5, 2))})
        gtts = []
        for i, sym in enumerate(held[1:3]):
            lp = last(sym)
            if not lp:
                continue
            trig = [round(lp * 0.9, 1)] if i == 0 else [round(lp * 0.92, 1), round(lp * 1.15, 1)]
            gtts.append({"symbol": sym, "kind": "SINGLE" if i == 0 else "TWO_LEG", "triggerPrices": trig,
                         "triggerDisplays": [format_price(t) for t in trig], "lastPriceAtSetup": lp, "quantity": 10.0,
                         "status": "active", "createdAt": f"{ss.as_of()}T10:15:00"})
        return build_activity(sample=True, connected=True, source=LABEL, as_of=ss.as_of(), positions=positions,
                              orders={"total": 3, "complete": 2, "open": 0, "cancelled": 1}, trades=2, gtts=gtts)

    def index_history(self, index_id: str, start: date, end: date) -> list[PricePoint]:
        ps = ss.index_prices(index_id)
        return [p for p in ps.points if start <= p[0] <= end] if ps else []


def build(config: dict, deps: dict) -> MockBroker:
    return MockBroker()
