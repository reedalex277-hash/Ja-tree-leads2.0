# Customer request form setup

1. Copy `supabase_customer_requests.sql` into the Supabase SQL Editor and run it. Do not open it in Creality.
2. In Vercel project settings, add `SUPABASE_URL` and `SUPABASE_SERVICE_ROLE_KEY` for the deployment environment. Get these from your Supabase project settings. Keep the service role key in Vercel only; never put it in HTML, browser JavaScript, screenshots or GitHub.
3. Upload these project files to the repository and redeploy.
4. Open `/request` on the deployed site and submit a test request.
5. In Supabase Table Editor, open `customer_requests` and verify the test row. Check the reference matches the form confirmation.

This uploaded project has a browser-only prospect board. Customer requests are saved to the separate private Supabase table. They do not appear in that board yet. A signed-in contractor inbox requires integration with the current live app and its existing authentication/ownership rules. No email or SMS notifications are configured.

The form uses a honeypot, body size limits, server validation and a request UUID to prevent duplicate rows when retrying. Before broadly advertising it, enable deployment-level rate limiting or add a verified CAPTCHA. The honeypot is not a complete abuse control.

The SQL changes only the new `customer_requests` table. If a table with that name already exists, check its schema before running this script. The endpoint requires the columns defined here.
