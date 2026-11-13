package com.stockanalyzer.engine;

import com.stockanalyzer.engine.model.FundInfo;
import com.stockanalyzer.engine.model.Kind;
import com.stockanalyzer.engine.model.PortfolioInput;
import com.stockanalyzer.engine.model.Position;
import com.stockanalyzer.engine.model.StockInfo;
import java.util.ArrayList;
import java.util.List;

/** An aggregated position with its current price and value. Positions without instrument data are dropped. */
public record ValuedPosition(Position position, String name, double price, double value, StockInfo stock, FundInfo fund) {

    public Kind kind() { return position.kind(); }

    public String id() { return position.id(); }

    public double cost() { return position.quantity() * position.avgPrice(); }

    public static List<ValuedPosition> of(PortfolioInput in) {
        List<ValuedPosition> out = new ArrayList<>();
        for (Position p : Position.aggregate(in.positions())) {
            if (p.kind() == Kind.STOCK) {
                StockInfo s = in.stocks().get(p.id());
                if (s == null) continue;
                out.add(new ValuedPosition(p, s.name(), s.lastPrice(), p.quantity() * s.lastPrice(), s, null));
            } else {
                FundInfo f = in.funds().get(p.id());
                if (f == null) continue;
                out.add(new ValuedPosition(p, f.name(), f.nav(), p.quantity() * f.nav(), null, f));
            }
        }
        return out;
    }

    public static double total(List<ValuedPosition> vps) {
        double t = 0;
        for (ValuedPosition v : vps) t += v.value();
        return t;
    }
}
