# Meal Matcher: Multi-Condition AI & Genetic Portion Meal Planner
#### Video Demo: <https://youtu.be/QSzxB8MARUA?si=tUG-PzbBiDOD21F_>
#### **Created by:** Asma Essaedi

Description:
Meal Matcher is a web-based clinical dietary management and wellness application built for calorie tracking and medical nutrition therapy. This app calculates daily nutritional targets based on the user's biometrics and dynamically applies medical guardrails based on user's chronic health conditions.


`requirements.txt`: This file stores dependencies the application depends upon:

- Flask - This is the web framework that handles the routing,request, response,template and the overall HTTP lifecycle
- Flask-Session - Flask session object is a server-side file that stores data about the user login state and meal plan results.
- cs50 - This is Harvard's CS50 library that provides the SQL() function.
- werkzeug - WSGI toolkit that is used for generate_password_hash() and check_password_hash() standard password security using PBKDF2 with salting.
- google-genai - This is the official Google Generative AI SDK that allows the call of the GEMINI 2.5 Flash model to generate meal plans from natural language prompts.
- python-dotenv - It allows the loading of environment variables from .env file into os.environ, so secrets, such as API keys and email passwords remain out of source code.

- gunicorn - A production-level WSGI HTTP server. It replaces Flask's built-in development server that for deployment.

**`app.py`:** This file is the heart of this web application. It imports standard python libraries, such as secrets, smtplib, time, json, os, functools plus every Flask and third-party library declared in the requirements.txt file.

The file starts by calling load_dotenv() to pull the credentials from the .env file, then instantiates the flask app and point it to the templates and static folders. Two key app configs are set: SESSION_PERMANENT = False so sessions expire when the browser closes and SECRET_KEY, which signs the session cookie.

Next, db = SQL() opens the SQLite database. The startup block then runs a CREATE TABLE IF NOT EXISTS statement to create the user_profiles table(if it is missing) and seeds the foods table with 30 nutritionally labelled ingredients using INSERT OR IGNORE, which insert each row only if the row with the same name does not already exist. This prevent duplicate entries on every app restart.

The helper functions that follow handle the application logic. get_ai_client() instantiates the Gemini client and raises a clear RuntimeError when the API key is missing or invalid. send_password_reset_email() composes and transmits a reset email over Google SMTP using smtplib and starttls.

calculate_meal_risks() loops through every ingredient in a generated meal, tallies, sodium cholesterol, glycemic index flags, protein, gluten, and FODMAP counts, and then maps those totals against each active medical condition to return a list of risk cards labelled "High Risk" or "Low Risk". filter_food_library() removes foods that conflict with active dietary preferences or medical conditions before passing the food library to the optimizer. get_or_create_profile() fetches the logged-in user's row from user_profiles. It also inserts a default row when one does not yet exist.


The login_required decorator wraps the route so any unauthenticated request is redirected to the login page.

The routes are:
-  /register, which validate the submitted email and password, hash the password with PBKDF2, inserts the new user row, and opens a session.
- /login, which looks up the user by email, verifies the hashed password, and stores user_id and username in the session.
- /logout takes the responsibilities of clearing the session and redirecting to the login page.
- /forgot-password, which generates a cryptographically random six-digit reset code, hashes and stores it with a 15-minutes expiry, and emails it to the user via send_password_reset_email().
- /reset-password, which validates the submitted code against the stored hash, checks the expiry timestamp, then updates the password hash and auto-logs the user in on success.

- /profile (GET/POST), on GET, renders the profile form pre-filled from the database. On POST, reads the submitted biometrics, conditions, and preferences, save them, then recalculates and save macro targets server-side as a fallback to the client-side JavaScript calculation.

- / (GET/POST) This is the main dashboard. On POST, it reads the chosen engine, targets, conditions, and preferences from the form. For the Gemini engine, it creates a detailed system instruction that insert the user's macros targets and active medical guardrails into the prompt, calls gemini-2.5-flash with response_mime_type="application/json". It, then, parse the returned JSON and stored the structured meal plan in the session before redirecting to /results. In case Gemini fails for any reason, the route automatically falls back to the genetic engine, which fetch the food library, filter it, and runs run_genetic_algorithm().

- /results reads the meal plan and engine type from the session, computes actual nutrients totals, calls calculate_meal_risk(), and render results.html with everything the template needs.

**`helpers.py`:**
This file contains the two main algorithm functions that power the Genetic Portion Optimizer engine.

calculate_fitness(meal, targets, conditions) is the evaluation function of the genetic algorithm. It loops through every ingredient in a meal, scales each nutrient by grams/100.0, and sums the total calories, protein, carbs, fat, sodium, and cholesterol. It then computes a weighted error score, where protein and carbs are multiplied by 6 and fat by 9, which allows for the overall calculation of their caloric densities and present how far the meal from the user's targets. After the base error is calculated, it applies conditional penalty blocks for each active medical condition. For hypertension, it adds a heavy penalty when sodium exceeds 1500mg, for diabetes and gestational diabetes penalize high glycemic ingredients and carbs overruns, and CKD penalizes protein above 60g, etc. Overall, a lower final score means a better meal.

generate_random_meal(food_library) creates a single random meal by sampling 3 to 5 unique foods from the library and assigning each a random portion between 50g and 300g.


run_genetic_algorithm(food_library, targets, conditions) begins by generating a random population of 50 meals. Each generation, the population is sorted by fitness score (ascending since lower is better) and the algorithm exits early if the best meal reaches a near perfect score below 10. The top 20% are kept as parents, and new child meals are bred by taking a random split of ingredients from two parents and applying a 20% chance mutation that shift one ingredient's portion by up to ±30g. After 100 generations (or early exit), the best score meal from the final sorted population is returned.

**`meal_matcher.db`:** This is the SQLite database file. It holds three tables. The users table stores each account's email, PBKDF2 password hash, and reset code data. The user_profile table stores one row per user with all physical metrics like age, gender, weight, height, activity level, goal, comma-separated strings for active conditions and preferences, and the four calculated macro targets. The foods table is the ingredient library that backs the genetic optimizer.


`layout.html`: This file is the base template. It composes of the HTML blueprint that other HTML files inherit from using Jinja2's {% extends %} system. <!DOCTYPE html> tells the browser this is an HTML5 document. <link rel="stylesheet"> tag load Outfit and Plus Jakarta Sans fonts from Google Fonts for modern typography. A {% if session.get("user_id") %} conditional renders different navigation links based on login state where authenticated users see Dashboard, My profile, and Logout, while guests see Login and Register. {% with messages = get_flashed_messages() %} renders flash messages, which is a one-time notifications Flask's flash() in python. The {% block body %}{% endblock %} is a Jinja2 template block that allows child templates like `index.html` to insert their content.

`index.html`: This file is the main dashboard template that the logged in user lands on. It extends layout.html and renders a personalized welcome card that displays the user's username, weight, height, and active goal pulled from session and profile context variables. Below that is the plan generation form. A hidden input name="engine" value="gemini"> field responsible of telling the backend which optimizer to use. To the right of the text is a panel exposing the four macro target input prefilled from the user's profile. Two accordion sections of checkboxes let the user select the medical condition/s and dietary preference/s that fit their needs. All checkboxes are pre-checked based on the conditions and preferences stored in the user's profile.

`profile.html`: This file is the wellness profile setup page. It extends layout.html and renders three panels for collecting Physical Metrics, Medical Conditions, and provide medical macros. The <script> block is the substantial part of this file as it implement real-time and client-side recalculation using the Mifflin-St Jeor equation for BMR (10 × weight + 6.25 × height − 5 × age + 5 for males, −161 for females). For computing the TDEE, BMR should be multiplied by an activity multiplier ranging from 1.2 (sedentary) to 1.9 (extra active). The calorie target is then adjusted by −500 for weight loss or +350 for muscle gain. Protein is set at 1.6g/kg of bodyweight by default, raised to 2.2g/kg when High Protein is selected, and capped at 60g when CKD is active. Fat allocation is 25% of calories normally, 40% for Low Carb, and 70% for Keto. The remaining calories after protein and fat are assigned as carbohydrates, with an additional 40% carb cap enforced when diabetes is checked. Whenever any input or checkbox changes, the macro fields and recommendation subtexts update instantly without a page reload.



**`styles.css`**:
This file is the single global stylesheet linked in layout.html. It defines the overall visual design system for the application using CSS custom properties for colors, spacing, border-radii, and shadows. It styles the header, navigation, footer, all form elements, the dashboard's two-column grid, the profile page's three-column grid, the results metrics cards, the recipe cards with their image overlays, the risk assessment grid, the nutrient totals table, and all authentication form containers. The stylesheet is mobile-friendly and uses @media queries to collapse multi-column layouts to single columns on narrow screens.

**`results.html`**: This file is the meal plan output page. It extends layout.html and renders different UI depending on which engine the backend stored in the session. A header box shows the active goals and an engine badge. Below that, if any medical conditions were active, a risk grid renders one card per condition produced by calculate_meal_risks(), coloured red for "High Risk" and green for "Low Risk". Then a six-card metrics grid shows the plan's actual totals for calories, protein, carbs, fat, sodium, and cholesterol alongside their targets. For gemini engine, the page renders a responsive grid of four recipe cards. One for each meal breakfast, lunch, dinner, and snack. Each card shows a Jinja2-selected Unsplash photograph that maps the meal title's keywords to the most relevant food image. A YouTube overlay on each image links to a video tutorial search and below the image is ingredients list, numbered instructions, and per-meal macro badges. For the Genetic engine, the page renders an HTML table with one row per ingredient, which shows food name, calculated portion weight, and per-portion values for calories, protein, carbs, fat, sodium, and cholesterol, alongside a YouTube video guide link. A "Back to Dashboard" button at the bottom closes the results view.


**`login.html`**, **`register.html`**, **`forgot_password.html`**, **`reset_password.html`**: These four files are the authentication templates, all extending layout.html. Each renders a centered form card with input fields, inline error and success messages via {% if error %} and {% if success %} blocks, and cross-links to the other auth pages.

**`script.js`**:
This file runs a DOMContentLoaded listener that attaches two submit-state handlers. The first targets the .prompt-form on the dashboard. On the submit it reads the selected engine, disables the submit button, and replace its label with contextual loading message, so the user knows the request is being processed. The second targets the .profile-form on the profile page and similarly disables and relabels the save button. These handlers prevent accidental double-submissions and give clear feedback during the seconds it takes the server to run inference or evolve a meal plan.
