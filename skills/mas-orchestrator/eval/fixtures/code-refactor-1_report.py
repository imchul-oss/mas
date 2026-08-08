# Eval fixture: one module carrying four unrelated concerns (config, fetch, format,
# persist) plus a scheduler loop. The refactor task is to split it into cohesive units
# WITHOUT changing behavior, and to argue how that is known. Several behaviors here are
# load-bearing and easy to break silently, which is the point.
import csv
import io
import json
import os
import time
import urllib.request

DEFAULTS = {"endpoint": "https://example.invalid/api/v1/metrics",
            "timeout": 10, "retries": 2, "currency": "USD", "decimals": 2}


def load_config(path=None):
    cfg = dict(DEFAULTS)
    if path and os.path.exists(path):
        with open(path, encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                if "=" not in line:
                    continue
                k, _, v = line.partition("=")
                k, v = k.strip(), v.strip()
                if k in ("timeout", "retries", "decimals"):
                    try:
                        cfg[k] = int(v)
                    except ValueError:
                        pass          # malformed numeric keeps the default, silently
                else:
                    cfg[k] = v
    for k in cfg:
        env = os.environ.get("REPORT_" + k.upper())
        if env is not None:
            cfg[k] = int(env) if k in ("timeout", "retries", "decimals") else env
    return cfg


def fetch_rows(cfg):
    last_err = None
    for attempt in range(cfg["retries"] + 1):
        try:
            req = urllib.request.Request(cfg["endpoint"], headers={"Accept": "application/json"})
            with urllib.request.urlopen(req, timeout=cfg["timeout"]) as resp:
                payload = json.loads(resp.read().decode("utf-8"))
            rows = payload.get("rows") or []
            return [r for r in rows if r.get("region")]
        except Exception as e:
            last_err = e
            if attempt < cfg["retries"]:
                time.sleep(0.5 * (2 ** attempt))     # exponential backoff
    raise RuntimeError("fetch failed after retries: %s" % last_err)


def money(value, cfg):
    try:
        v = float(value)
    except (TypeError, ValueError):
        return ""
    s = ("%%.%df" % cfg["decimals"]) % v
    whole, _, frac = s.partition(".")
    neg = whole.startswith("-")
    if neg:
        whole = whole[1:]
    grouped = ""
    while len(whole) > 3:
        grouped = "," + whole[-3:] + grouped
        whole = whole[:-3]
    grouped = whole + grouped
    out = grouped + ("." + frac if frac else "")
    if neg:
        out = "-" + out
    return cfg["currency"] + " " + out


def summarize(rows, cfg):
    by_region = {}
    for r in rows:
        region = r["region"]
        bucket = by_region.setdefault(region, {"region": region, "count": 0, "total": 0.0})
        bucket["count"] += 1
        try:
            bucket["total"] += float(r.get("amount") or 0)
        except (TypeError, ValueError):
            pass
    ordered = sorted(by_region.values(), key=lambda b: (-b["total"], b["region"]))
    for b in ordered:
        b["total_display"] = money(b["total"], cfg)
        b["average_display"] = money(b["total"] / b["count"] if b["count"] else 0, cfg)
    return ordered


def to_csv(summary):
    buf = io.StringIO()
    w = csv.writer(buf, lineterminator="\n")
    w.writerow(["region", "count", "total", "average"])
    for b in summary:
        w.writerow([b["region"], b["count"], b["total_display"], b["average_display"]])
    return buf.getvalue()


def write_report(text, out_dir, stamp):
    os.makedirs(out_dir, exist_ok=True)
    tmp = os.path.join(out_dir, ".report-%s.tmp" % stamp)
    final = os.path.join(out_dir, "report-%s.csv" % stamp)
    with open(tmp, "w", encoding="utf-8", newline="") as fh:
        fh.write(text)
    os.replace(tmp, final)              # atomic publish; readers never see a partial file
    return final


def prune(out_dir, keep=7):
    names = sorted(n for n in os.listdir(out_dir) if n.startswith("report-") and n.endswith(".csv"))
    for n in names[:-keep] if len(names) > keep else []:
        os.remove(os.path.join(out_dir, n))


def run_once(config_path, out_dir, stamp):
    cfg = load_config(config_path)
    rows = fetch_rows(cfg)
    summary = summarize(rows, cfg)
    path = write_report(to_csv(summary), out_dir, stamp)
    prune(out_dir)
    return path


def main(config_path=None, out_dir="out", interval=3600, cycles=None):
    n = 0
    while cycles is None or n < cycles:
        stamp = time.strftime("%Y%m%d-%H%M%S", time.gmtime())
        try:
            run_once(config_path, out_dir, stamp)
        except Exception as e:
            print("cycle failed: %s" % e)     # a failed cycle never stops the loop
        n += 1
        if cycles is None or n < cycles:
            time.sleep(interval)
