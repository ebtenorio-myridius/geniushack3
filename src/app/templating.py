from pathlib import Path

from fastapi.templating import Jinja2Templates

def demo_identity_context(request):
	role = request.cookies.get("demo_role")
	role_labels = {
		"product_owner": "Product owner",
		"analyst": "FCRM analyst",
		"committee": "Risk committee member",
		"administrator": "System administrator",
	}
	return {
		"current_demo_user": request.cookies.get("demo_user"),
		"current_demo_role": role,
		"current_demo_role_label": role_labels.get(role),
	}


templates = Jinja2Templates(
	directory=str(Path(__file__).parent / "templates"),
	context_processors=[demo_identity_context],
)
