"""All sentence templates. TEMPLATES: id -> (text, {fact key: unit}).

Placeholders: {key} inserts the display string; {key|one|many} inserts '<n> one' or '<n> many' for a COUNT.
pf.* and tio.* are contract B.12 (exact text). stk.*, fnd.*, glossary.* are internal to this service.
"""
from __future__ import annotations


def _t(spec: str) -> dict[str, str]:
    out = {}
    for tok in spec.split():
        k, u = tok.split(":")
        out[k] = u
    return out


_RAW: list[tuple[str, str, str]] = [
    # ------------------------------------------------------------------ contract B.12 (portfolio + try it on)
    ("pf.summary.value", "Your holdings are worth {totalValueInr} across {stockCount|stock|stocks} and {fundCount|mutual fund|mutual funds}.", "totalValueInr:INR stockCount:COUNT fundCount:COUNT"),
    ("pf.summary.empty", "You have not added any holdings yet. Connect your Zerodha account or add a statement to see what you own.", ""),
    ("pf.summary.top_exposure", "Your largest single company exposure is {companyName} at {companyPct} of your holdings, {directPct} held directly and {throughFundsPct} through funds.", "companyName:TEXT companyPct:PCT directPct:PCT throughFundsPct:PCT"),
    ("pf.summary.returns", "Over the last {windowLabel}, your current holdings moved {portfolioReturnPct} while the Nifty 50 moved {niftyReturnPct}.", "windowLabel:TEXT portfolioReturnPct:PCT_CHANGE niftyReturnPct:PCT_CHANGE"),
    ("pf.summary.returns_unavailable", "There is not enough price history yet to compare your holdings with the Nifty 50 over the last {windowLabel}.", "windowLabel:TEXT"),
    ("pf.fact.overlap", "{fundA} and {fundB} hold {commonCount|company|companies} in common, adding up to an overlap of {overlapPct}.", "fundA:TEXT fundB:TEXT overlapPct:PCT commonCount:COUNT"),
    ("pf.fact.overlap_none", "With {fundCount|fund|funds}, there is no pair of funds to compare for overlap.", "fundCount:COUNT"),
    ("pf.fact.cost", "Your funds cost about {yearlyCostInr} a year in fees. Regular plans add {regularGapInr} a year compared with the direct plans of the same funds.", "yearlyCostInr:INR regularGapInr:INR"),
    ("pf.fact.cost_direct_only", "Your funds cost about {yearlyCostInr} a year in fees, and all of them are direct plans.", "yearlyCostInr:INR"),
    ("pf.fact.cost_none", "You hold no mutual funds, so there is no yearly fund fee.", ""),
    ("pf.fact.idle_cash", "{idleCashInr} is sitting as cash in your trading account, {idleCashPct} of your holdings plus cash.", "idleCashInr:INR idleCashPct:PCT"),
    ("pf.fact.idle_cash_none", "No idle cash was reported in your trading account.", ""),
    ("pf.exposure.company", "{companyName} is your largest company exposure at {companyPct}: {directPct} direct and {throughFundsPct} through funds. You own pieces of {companyCount|company|companies} in all.", "companyName:TEXT companyPct:PCT directPct:PCT throughFundsPct:PCT companyCount:COUNT"),
    ("pf.exposure.sector", "{sectorName} is your largest sector at {sectorPct}, out of {sectorCount|sector|sectors}.", "sectorName:TEXT sectorPct:PCT sectorCount:COUNT"),
    ("pf.exposure.size", "By company size: large {largePct}, mid {midPct}, small {smallPct}, micro {microPct}; debt and cash {debtCashPct}.", "largePct:PCT midPct:PCT smallPct:PCT microPct:PCT debtCashPct:PCT"),
    ("pf.exposure.other", "{otherPct} of your money sits in fund holdings that are not disclosed company by company, shown as Other / undisclosed.", "otherPct:PCT"),
    ("pf.concentration", "Your five largest company exposures add up to {top5Pct} of your holdings, across {holdingCount|holding|holdings}.", "top5Pct:PCT holdingCount:COUNT"),
    ("pf.mix.equity_debt", "{equityPct} of your money is in shares, {debtCashPct} in debt and cash, and {otherPct} in other assets.", "equityPct:PCT debtCashPct:PCT otherPct:PCT"),
    ("pf.mix.stocks_funds", "{stocksPct} is in stocks you hold directly and {fundsPct} is in mutual funds.", "stocksPct:PCT fundsPct:PCT"),
    ("pf.returns.since_buy", "Since you first invested, {coveredCount|holding|holdings} with known purchase dates moved {portfolioGainPct}; the same money put into the Nifty 50 on the same dates would have moved {niftySameDatesPct}.", "portfolioGainPct:PCT_CHANGE niftySameDatesPct:PCT_CHANGE coveredCount:COUNT"),
    ("pf.returns.since_buy_unavailable", "Purchase dates are not available for your holdings, so a same-period comparison with the Nifty 50 is not shown.", ""),
    ("tio.assumption.lump_sum", "This shows your portfolio with a one-time {amountInr} added to {instrumentName} at today's price.", "instrumentName:TEXT amountInr:INR"),
    ("tio.assumption.sip", "This shows your portfolio with {amountInr} a month added to {instrumentName} for {months|month|months} ({totalInr} in all), assuming prices stay where they are today.", "instrumentName:TEXT amountInr:INR months:COUNT totalInr:INR"),
    ("tio.largest_company", "Largest company exposure: {beforeName} at {beforePct} before, {afterName} at {afterPct} after.", "beforeName:TEXT beforePct:PCT afterName:TEXT afterPct:PCT"),
    ("tio.top_sector", "Largest sector: {beforeName} at {beforePct} before, {afterName} at {afterPct} after.", "beforeName:TEXT beforePct:PCT afterName:TEXT afterPct:PCT"),
    ("tio.size_mix", "{bandName} share: {beforePct} before, {afterPct} after.", "bandName:TEXT beforePct:PCT afterPct:PCT"),
    ("tio.holdings_count", "Number of holdings: {beforeCount} before, {afterCount} after.", "beforeCount:COUNT afterCount:COUNT"),
    ("tio.holdings_count_same", "Number of holdings stays at {count}, because you already hold it.", "count:COUNT"),
    ("tio.overlap_fund", "{instrumentName} overlaps most with {fundName}, at {overlapPct}.", "instrumentName:TEXT fundName:TEXT overlapPct:PCT"),
    ("tio.overlap_stock", "{instrumentName} is already inside {fundsHoldingCount|fund|funds} you hold; your total exposure to it goes from {beforePct} to {afterPct}.", "instrumentName:TEXT fundsHoldingCount:COUNT beforePct:PCT afterPct:PCT"),
    ("tio.overlap_none_fund", "{instrumentName} has no companies in common with the funds you hold.", "instrumentName:TEXT"),
    ("tio.overlap_none_stock", "{instrumentName} is not inside any fund you hold; your exposure to it goes from {beforePct} to {afterPct}.", "instrumentName:TEXT beforePct:PCT afterPct:PCT"),
    ("tio.cost", "Yearly fund fees: {beforeInr} before, {afterInr} after.", "beforeInr:INR afterInr:INR"),
    ("tio.cost_stock", "Adding a stock adds no yearly fund fee; it stays at {beforeInr}.", "beforeInr:INR"),

    # ------------------------------------------------------------------ glossary explain
    ("glossary.explain.with_typical", "For {instrumentName} this is {thisFigure}; {typicalLabel} is {typical}.", "instrumentName:TEXT thisFigure:TEXT typicalLabel:TEXT typical:TEXT"),
    ("glossary.explain.no_typical", "For {instrumentName} this is {thisFigure}.", "instrumentName:TEXT thisFigure:TEXT"),

    # ------------------------------------------------------------------ stock answers
    ("stk.business.about", "{companyName} {about}", "companyName:TEXT about:TEXT"),
    ("stk.business.revenue", "It earned {revenue} in revenue in {fy}, {change} {prevRevenue} in {prevFy}.", "revenue:INR fy:TEXT change:TEXT prevRevenue:INR prevFy:TEXT"),
    ("stk.business.segment", "{segmentName} accounts for {share} of revenue, the largest single business.", "segmentName:TEXT share:PCT"),
    ("stk.growth.revenue", "Over the last three years, revenue {verb} by {revenueCagr} a year on average; the median for its {peerGroup} peers is {peerRevenueCagr}.", "verb:TEXT revenueCagr:PCT peerGroup:TEXT peerRevenueCagr:PCT"),
    ("stk.growth.profit", "Net profit {verb} by {profitCagr} a year on average over the same period (peer median {peerProfitCagr}) and was {netProfit} in {fy}.", "verb:TEXT profitCagr:PCT peerProfitCagr:PCT netProfit:INR fy:TEXT"),
    ("stk.growth.profit_na", "Net profit was {netProfit} in {fy} and {prevNetProfit} in {prevFy}, so a yearly growth rate cannot be worked out.", "netProfit:INR fy:TEXT prevNetProfit:INR prevFy:TEXT"),
    ("stk.growth.margin_roe", "In {fy} the company kept {operatingMargin} of its revenue as operating profit (five-year median {ownMedian}, peer median {peerMargin}) and earned {roe} on shareholders' money (peer median {peerRoe}).", "fy:TEXT operatingMargin:PCT ownMedian:PCT peerMargin:PCT roe:PCT peerRoe:PCT"),
    ("stk.safety.debt", "The company owed {debt} in {fy}, {change} {prevDebt} in {prevFy}, and held {cash} in cash.", "debt:INR fy:TEXT change:TEXT prevDebt:INR prevFy:TEXT cash:INR"),
    ("stk.safety.ratio", "Its debt is {debtToEquity} the money shareholders have put in; the five-year median is {ownMedian} and the peer median is {peerMedian}.", "debtToEquity:TIMES ownMedian:TIMES peerMedian:TIMES"),
    ("stk.safety.coverage", "Yearly operating profit was {coverage} the yearly interest bill; the peer median is {peerMedian}.", "coverage:TIMES peerMedian:TIMES"),
    ("stk.safety.coverage_none", "The company reported no interest cost in {fy}, so interest cover is not worked out.", "fy:TEXT"),
    ("stk.safety.fin_intro", "{companyName} is a bank or lender, so deposits and borrowings are its raw material and the debt ratios used for other companies do not apply.", "companyName:TEXT"),
    ("stk.safety.fin_networth", "Shareholders' money stood at {netWorth} in {fy}, {change} {prevNetWorth} in {prevFy}.", "netWorth:INR fy:TEXT change:TEXT prevNetWorth:INR prevFy:TEXT"),
    ("stk.safety.fin_roe", "It earned {roe} on that money in {fy}; the peer median is {peerRoe}.", "roe:PCT fy:TEXT peerRoe:PCT"),
    ("stk.price.pe", "The share price is {pe} the yearly profit per share. That is {ownPos} the company's own five-year median of {ownPe} and {peerPos} the peer median of {peerPe}.", "pe:TIMES ownPos:TEXT ownPe:TIMES peerPos:TEXT peerPe:TIMES"),
    ("stk.price.pe_loss", "The company made a loss over the last four quarters, so a price to yearly profit ratio cannot be worked out; the peer median is {peerPe}.", "peerPe:TIMES"),
    ("stk.price.pb", "The share price is {pb} the shareholders' money per share (book value), {ownPos} its own five-year median of {ownPb} and {peerPos} the peer median of {peerPb}.", "pb:TIMES ownPos:TEXT ownPb:TIMES peerPos:TEXT peerPb:TIMES"),
    ("stk.price.cap", "The whole company is valued at {marketCap} on the market, against {prevMarketCap} a year ago, and its dividend yield is {dividendYield} (peer median {peerYield}).", "marketCap:INR prevMarketCap:INR dividendYield:PCT peerYield:PCT"),
    ("stk.recent.results", "In {quarterLabel}, revenue changed by {revenueYoy} and net profit by {profitYoy} compared with the same quarter a year earlier (results announced {resultsDate}).", "quarterLabel:TEXT revenueYoy:PCT_CHANGE profitYoy:PCT_CHANGE resultsDate:TEXT"),
    ("stk.recent.results_profit_na", "In {quarterLabel}, revenue changed by {revenueYoy} compared with the same quarter a year earlier; the profit change cannot be worked out because that earlier quarter was a loss (results announced {resultsDate}).", "quarterLabel:TEXT revenueYoy:PCT_CHANGE resultsDate:TEXT"),
    ("stk.recent.results_none", "Quarterly results are not available in the data for this company.", ""),
    ("stk.recent.price", "Over the last 90 days the share price changed by {priceChange}, while the Nifty 50 changed by {niftyChange}.", "priceChange:PCT_CHANGE niftyChange:PCT_CHANGE"),
    ("stk.recent.price_na", "There is not enough price history to show the last 90 days.", ""),
    ("stk.recent.event", "Latest company update, on {eventDate}: {eventText}", "eventDate:TEXT eventText:TEXT"),
    ("stk.recent.event_none", "No other company announcements are listed in the last three months.", ""),

    # ------------------------------------------------------------------ stock facts
    ("stk.fact.promoter_holding", "Promoters own {holding} of the company, {direction} {prevHolding} four quarters ago.", "holding:PCT direction:TEXT prevHolding:PCT"),
    ("stk.fact.promoter_holding_none", "No promoter holding is reported for {companyName}.", "companyName:TEXT"),
    ("stk.fact.promoter_pledge", "{pledge} of the promoters' shares are pledged as security for loans, against {prevPledge} four quarters ago.", "pledge:PCT prevPledge:PCT"),
    ("stk.fact.promoter_pledge_none", "None of the promoters' shares are pledged as security for loans.", ""),
    ("stk.fact.promoter_pledge_nopromoter", "Promoters hold no shares in the data, so there is no pledge to report.", ""),
    ("stk.fact.profit", "The company reported {profit1} in {fy1}, {profit2} in {fy2} and {profit3} in {fy3}.", "profit1:TEXT fy1:TEXT profit2:TEXT fy2:TEXT profit3:TEXT fy3:TEXT"),
    ("stk.fact.profit_all", "Each of the three years ended with a profit.", ""),
    ("stk.fact.profit_loss", "{lossCount|year|years} in this period ended with a net loss.", "lossCount:COUNT"),
    ("stk.fact.profit_na", "Fewer than three years of yearly results are available for this company.", ""),
    ("stk.fact.debt_to_profit", "Total debt of {debt} is {ratio} the latest yearly net profit of {profit}.", "debt:INR ratio:TIMES profit:INR"),
    ("stk.fact.debt_to_profit_cmp", "Three years earlier this figure was {ownPrev}; the peer median is {peerMedian}.", "ownPrev:TIMES peerMedian:TIMES"),
    ("stk.fact.debt_loss", "The company made a net loss of {loss} in {fy} while owing {debt}, so debt cannot be measured against yearly earnings.", "loss:INR fy:TEXT debt:INR"),
    ("stk.fact.debt_financial", "Debt against yearly earnings is not shown for {companyName} because deposits and borrowings are a bank's or lender's raw material.", "companyName:TEXT"),
    ("stk.fact.price_move", "The share price changed by {priceChange} in the last 30 days, while the Nifty 50 changed by {niftyChange}.", "priceChange:PCT_CHANGE niftyChange:PCT_CHANGE"),
    ("stk.fact.price_move_only", "The share price changed by {priceChange} in the last 30 days.", "priceChange:PCT_CHANGE"),
    ("stk.fact.results_yes", "Quarterly results were announced in this period, on {resultsDate}.", "resultsDate:TEXT"),
    ("stk.fact.results_no", "No quarterly results were announced in this period.", ""),
    ("stk.fact.price_move_na", "There are fewer than 30 days of prices in the data, so the 30-day move is not shown.", ""),
    ("stk.fact.avg_traded", "On an average day over the last 20 trading sessions, shares worth {adtv} changed hands.", "adtv:INR"),
    ("stk.fact.avg_traded_cmp", "A year earlier the same figure was {prevAdtv}; the peer median is {peerAdtv}.", "prevAdtv:INR peerAdtv:INR"),
    ("stk.fact.avg_traded_na", "Trading volumes are not available in the data, so the average daily trading value is not shown.", ""),
    ("stk.fact.size_band", "{companyName} is a {bandLabel} company, valued at {marketCap} on the market.", "companyName:TEXT bandLabel:TEXT marketCap:INR"),
    ("stk.fact.size_rank", "It ranks {rank} by market value; the lower limit for {bandLabel} companies is {cutoff}.", "rank:COUNT bandLabel:TEXT cutoff:INR"),
    ("stk.fact.size_rank_nolimit", "It ranks {rank} by market value; there is no lower limit for {bandLabel} companies.", "rank:COUNT bandLabel:TEXT"),
    ("stk.fact.surv_on", "{companyName} is on the NSE surveillance lists: {status}.", "companyName:TEXT status:TEXT"),
    ("stk.fact.surv_off", "{companyName} is not on the NSE ASM, GSM or ESM surveillance lists.", "companyName:TEXT"),
    ("stk.fact.surv_note", "These lists mark stocks that the exchange watches more closely and applies extra trading checks to.", ""),
    ("stk.fact.surv_na", "The surveillance lists could not be reached, so the status is not shown.", ""),

    ("stk.generic.na", "Some figures for this question are not available in the data used for {companyName}.", "companyName:TEXT"),
    ("fnd.generic.na", "Some figures for this question are not available in the data used for {fundName}.", "fundName:TEXT"),

    # ------------------------------------------------------------------ drawdown (stock + fund)
    ("stk.drawdown.fall", "Over {windowLabel}, the worst fall in the share price was {fall}, from {peakDate} to {troughDate}.", "windowLabel:TEXT fall:PCT peakDate:TEXT troughDate:TEXT"),
    ("stk.drawdown.recovered", "It took {days} from the lowest point to get back to the earlier high.", "days:DAYS"),
    ("stk.drawdown.not_recovered", "It had not got back to the earlier high by {asOfDate}.", "asOfDate:TEXT"),
    ("stk.drawdown.benchmark", "Over the same period the worst fall in the Nifty 50 was {benchFall}.", "benchFall:PCT"),
    ("stk.drawdown.none", "The price did not fall below an earlier high in this period.", ""),
    ("fnd.drawdown.fall", "Over {windowLabel}, the worst fall in the fund's value was {fall}, from {peakDate} to {troughDate}.", "windowLabel:TEXT fall:PCT peakDate:TEXT troughDate:TEXT"),
    ("fnd.drawdown.recovered", "It took {days} from the lowest point to get back to the earlier high.", "days:DAYS"),
    ("fnd.drawdown.not_recovered", "It had not got back to the earlier high by {asOfDate}.", "asOfDate:TEXT"),
    ("fnd.drawdown.benchmark", "Over the same period the worst fall in its benchmark, {benchName}, was {benchFall}.", "benchName:TEXT benchFall:PCT"),
    ("fnd.drawdown.none", "The fund's value did not fall below an earlier high in this period.", ""),

    # ------------------------------------------------------------------ fund answers
    ("fnd.holdings.what", "{fundName} is a {category} from {amc}; its money is {equityPct} in shares, {debtPct} in debt and {cashPct} in cash and similar assets.", "fundName:TEXT category:TEXT amc:TEXT equityPct:PCT debtPct:PCT cashPct:PCT"),
    ("fnd.holdings.top", "It lists {count|company|companies} in its portfolio, and the largest are {top1Name} ({top1Weight}), {top2Name} ({top2Weight}) and {top3Name} ({top3Weight}).", "count:COUNT top1Name:TEXT top1Weight:PCT top2Name:TEXT top2Weight:PCT top3Name:TEXT top3Weight:PCT"),
    ("fnd.holdings.debt_only", "It does not hold shares of companies; its money is in bonds and other debt papers and in cash.", ""),
    ("fnd.holdings.managers", "It is run by {managerNames}; the longest-serving manager has been in charge for {tenure}.", "managerNames:TEXT tenure:YEARS"),
    ("fnd.perf.period", "Over {periodLabel} the fund returned {fundReturn} a year, {benchPos} its benchmark ({benchName}) at {benchReturn} and {catPos} the {category} average of {catReturn}.", "periodLabel:TEXT fundReturn:PCT benchPos:TEXT benchName:TEXT benchReturn:PCT catPos:TEXT category:TEXT catReturn:PCT"),
    ("fnd.perf.period_nobench", "Over {periodLabel} the fund returned {fundReturn} a year, and the {category} average is {catReturn}.", "periodLabel:TEXT fundReturn:PCT category:TEXT catReturn:PCT"),
    ("fnd.perf.na", "The fund is younger than {periodLabel}, so no figure is shown for that period.", "periodLabel:TEXT"),
    ("fnd.bump.rupees", "On {amount}, the fund's worst fall of {fall} would have been about {rupeeFall} between its high and its low point.", "amount:INR fall:PCT rupeeFall:INR"),
    ("fnd.bump.compare", "Over the same dates the worst fall in its benchmark was {benchFall}, and the {category} average worst fall is {catFall}.", "benchFall:PCT category:TEXT catFall:PCT"),
    ("fnd.bump.recovered", "It took {days} from the lowest point to get back to the earlier high.", "days:DAYS"),
    ("fnd.bump.not_recovered", "It had not got back to the earlier high by {asOfDate}.", "asOfDate:TEXT"),
    ("fnd.bump.none", "The fund's value has not fallen below an earlier high in the period covered.", ""),
    ("fnd.cost.yearly", "On {amount} ({amountNote}) the fund charges about {yearlyCost} a year, an expense ratio of {ter}; the {category} median for {planLabel} plans is {median}.", "amount:INR amountNote:TEXT yearlyCost:INR ter:PCT category:TEXT planLabel:TEXT median:PCT"),
    ("fnd.cost.gap_regular", "The direct plan of the same fund would charge {twinCost} on the same amount, so the regular plan costs {gap} more each year.", "twinCost:INR gap:INR"),
    ("fnd.cost.gap_direct", "The regular plan of the same fund would charge {twinCost} on the same amount, which is {gap} more each year than this direct plan.", "twinCost:INR gap:INR"),
    ("fnd.cost.no_twin", "No direct or regular twin of this fund is known, so no plan comparison is shown.", ""),
    ("fnd.cost.how", "The fee is taken out of the fund's value every day, so it is never billed to you separately.", ""),
    ("fnd.recent.aum", "The fund's size is {aum}, compared with {aumPrev} a year earlier, a change of {change}.", "aum:INR aumPrev:INR change:PCT_CHANGE"),
    ("fnd.recent.top10", "Compared with last month, {added} entered the ten largest holdings and {dropped} left them.", "added:TEXT dropped:TEXT"),
    ("fnd.recent.top10_same", "The ten largest holdings are the same companies as last month.", ""),
    ("fnd.recent.top10_na", "Last month's list of largest holdings is not available for comparison.", ""),
    ("fnd.recent.event", "Latest fund update, on {eventDate}: {eventText}", "eventDate:TEXT eventText:TEXT"),
    ("fnd.recent.event_none", "No manager, benchmark or fee changes are listed in the last six months.", ""),

    # ------------------------------------------------------------------ fund facts
    ("fnd.fact.plan_regular", "This is the regular plan, which pays a distributor a commission; on {amount} the direct plan of the same fund would cost {gap} less each year.", "amount:INR gap:INR"),
    ("fnd.fact.plan_direct", "This is the direct plan, which pays no distributor commission; on {amount} the regular plan of the same fund would cost {gap} more each year.", "amount:INR gap:INR"),
    ("fnd.fact.plan_no_twin", "This is a {planLabel} plan, and no matching {otherLabel} plan is known, so the yearly cost difference is not shown.", "planLabel:TEXT otherLabel:TEXT"),
    ("fnd.fact.expense", "The yearly fee is {ter}, which is {pos} the {category} median of {median} for {planLabel} plans.", "ter:PCT pos:TEXT category:TEXT median:PCT planLabel:TEXT"),
    ("fnd.fact.expense_rupees", "On {amount} that is {cost} a year.", "amount:INR cost:INR"),
    ("fnd.fact.age", "The fund was launched on {launchDate}, {age} ago; the {category} median age is {medianAge}.", "launchDate:TEXT age:YEARS category:TEXT medianAge:YEARS"),
    ("fnd.fact.size", "It manages {aum} of investors' money; the {category} median is {medianAum}.", "aum:INR category:TEXT medianAum:INR"),
    ("fnd.fact.trailed", "The fund returned less than its benchmark in {trailed|year|years} out of the last {total|year|years} ({firstYear} to {lastYear}).", "trailed:COUNT total:COUNT firstYear:TEXT lastYear:TEXT"),
    ("fnd.fact.trailed_cmp", "The {category} average is {catAvg} out of five.", "category:TEXT catAvg:YEARS"),
    ("fnd.fact.trailed_na", "Fewer than five full calendar years of history are available, so only the years that exist are counted.", ""),
    ("fnd.fact.mandate", "{category}: {mayHold}", "category:TEXT mayHold:TEXT"),
    ("fnd.fact.mandate_equity", "This fund holds {equity} in shares; the minimum for the category is {minimum}.", "equity:PCT minimum:PCT"),
    ("fnd.fact.mandate_nomin", "This fund holds {equity} in shares; the category has no required minimum for shares.", "equity:PCT"),
    ("fnd.fact.top10", "The ten largest holdings make up {share} of the fund; the {category} median is {median}.", "share:PCT category:TEXT median:PCT"),
    ("fnd.fact.top10_largest", "The single largest holding is {name} at {weight}.", "name:TEXT weight:PCT"),
    ("fnd.fact.top10_na", "The holdings of this fund are not listed company by company in the data available, so the share of the ten largest is not shown.", ""),
    ("fnd.fact.exit_load", "Exit load is a fee charged if you take money out early: {exitLoad}.", "exitLoad:TEXT"),
    ("fnd.fact.exit_none", "There is no exit load, so money can be taken out at any time without that fee.", ""),
    ("fnd.fact.lockin_none", "There is no lock-in period.", ""),
    ("fnd.fact.lockin_yes", "Money is locked in for {lockIn} and cannot be taken out before that.", "lockIn:YEARS"),
    ("fnd.fact.overlap_top", "{fundName} is the fund you hold that this one overlaps with most, at {overlapPct} with {commonCount|company|companies} in common.", "fundName:TEXT overlapPct:PCT commonCount:COUNT"),
    ("fnd.fact.overlap_rest", "It also overlaps with {restCount|other fund|other funds} you hold; each figure is listed below.", "restCount:COUNT"),
    ("fnd.fact.overlap_none", "You hold no other mutual funds, so there is no overlap to show.", ""),
]

TEMPLATES: dict[str, tuple[str, dict[str, str]]] = {}
for _id, _text, _spec in _RAW:
    assert _id not in TEMPLATES, _id
    TEMPLATES[_id] = (_text, _t(_spec))
