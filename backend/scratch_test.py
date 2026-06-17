import os
import sys
# Make sure backend package can be imported
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.crews.marketing_crew import marketing_crew

print("Running marketing crew...")
try:
    result = marketing_crew.run(
        product_name="Munnar Cardamom",
        description="Organic green cardamom from Munnar hills.",
        location="Kerala, India",
        product_images=[],
        version=1
    )
    print("SUCCESS!")
    print(result.keys())
except Exception as e:
    print("FAILED!")
    import traceback
    traceback.print_exc()
