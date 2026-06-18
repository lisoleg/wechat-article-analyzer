"""Read crawl log and print with utf-8 decoding."""
import sys

log_file = sys.argv[1] if len(sys.argv) > 1 else "crawl_utf8.log"

with open(log_file, "rb") as f:
    raw = f.read()

# Try to decode as utf-8 first, then gbk
try:
    text = raw.decode("utf-8")
except UnicodeDecodeError:
    text = raw.decode("gbk", errors="replace")

# Print last 60 lines - write to file to avoid terminal encoding issues
out_file = log_file + ".out.txt"
with open(out_file, "w", encoding="utf-8") as f:
    lines = text.splitlines()
    for line in lines[-80:]:
        f.write(line + "\n")

print(f"日志已写入: {out_file}")
if len(lines) > 80:
    print(f"（共 {len(lines)} 行，显示最后 80 行）")
