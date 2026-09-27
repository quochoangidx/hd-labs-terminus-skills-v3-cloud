import json, random, sys
from pathlib import Path
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[2] / "tasks" / "tbrain-car-rental-agreement-billing" / "solution"))
sys.path.insert(0, sys.argv[1] if len(sys.argv) > 1 else str(HERE / "oracle" / "app" / "src"))
sys.path.insert(0, str(HERE))
import model, gen
from rentcharge import bill_run
bad = 0
for i in range(500):
    f = gen.agreement_file(random.Random(i))
    if bill_run(f) != model.report(f):
        bad += 1
print("mismatch", bad)
