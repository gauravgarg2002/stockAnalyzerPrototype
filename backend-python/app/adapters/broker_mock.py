"""Mock broker: instant connect; portfolio from sample_user.json + sample prices."""
from __future__ import annotations

from datetime import date

from .. import errors, sources
from . import sample_store as ss
from .base import BrokerPortfolio, PricePoint

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


def build(config: dict, deps: dict) -> MockBroker:
    return MockBroker()
