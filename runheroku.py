from standings import app
import os
interface = os.environ['app_binding_address']
port = int(os.environ.get("PORT", 5000))


app.run(host=interface, port=port, debug=False)
