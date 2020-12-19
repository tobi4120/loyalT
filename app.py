from flask import Flask, render_template, request, flash, redirect, url_for, session
from flask_session import Session
from cs50 import SQL
import zlib
from datetime import datetime
import pytz
from matplotlib import pyplot as plt
import matplotlib
matplotlib.use('pdf')
import matplotlib.ticker as ticker
from matplotlib import dates as mpl_dates
import calendar

# Create a secret key
app=Flask(__name__)
app.config['SECRET_KEY'] = "_2f!qX3n^DP-2s@R"
app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 0

# Connect to SQL server
db = SQL("sqlite:///LoyalT.db")

PYTHONHASHSEED=0

@app.route("/")
def welcome():

    #Clear session when users arrive on the welcome page
    session.clear()
    return render_template("welcome.html")

@app.route("/login", methods=["GET", "POST"])
def login():

    session.clear()

    # Check to see if the username entered exists and if so check to see if the password enters matches the password in the database
    if request.method == "POST":
        result = db.execute("SELECT id, username, hash FROM users WHERE username=:username", username = request.form.get("username"))

        if len(result) != 1:
            flash("Username does not exist!")
            return render_template("login.html")
        elif str(zlib.adler32(bytes(request.form.get("password"), encoding='utf8'))) != result[0]['hash']:
            flash("Password is incorrect!")
            return render_template("login.html")
        else:
            session["user_id"] = result[0]["id"]
            return redirect(url_for('homepage'))
    else:
        return render_template("login.html")

@app.route("/signup", methods=["GET", "POST"])
def signup():

    session.clear()

    # Checks to see if username exists and password and password confirmation match. If so add user to database and redirect to homepage
    if request.method == "POST":
        result = db.execute("SELECT * FROM users WHERE username=:username", username = request.form.get("sign-username"))

        if len(result) == 1:
            flash("Username already exists!")
            return render_template("signup.html")
        elif request.form.get("sign-password") != request.form.get("sign-confirm-password"):
            flash("Password and password confirmation do not match!")
            return render_template("signup.html")
        else:
            db.execute("INSERT INTO users (username, hash) VALUES (:username, :password)",
            username = request.form.get("sign-username"), password = str(zlib.adler32(bytes(request.form.get("sign-password"), encoding='utf8'))))

            result2 = db.execute("SELECT id FROM users WHERE username=:username", username = request.form.get("sign-username"))

            session["user_id"] = result2[0]["id"]

            flash("You have been registered!", "success")
            return redirect(url_for('homepage'))
    else:
        return render_template("signup.html")

@app.route("/homepage")
def homepage():
    if not session:
        return redirect(url_for('login'))
    else:

        # Get the promotion information for all promotions that the user has created
        promotion_list = db.execute("""SELECT promotion_name, start_date, end_date, purchase_number, reward FROM promotions WHERE user_id=:user_id
        ORDER BY start_date DESC""", user_id=session["user_id"])

        return render_template("homepage.html", promotion_list=promotion_list)

@app.route("/new-promotion", methods=["GET", "POST"])
def newpromotion():
    if not session:
        return redirect(url_for('login'))
    else:
        if request.method == "POST":

            promo_name = request.form.get("promotion-name")

            result=db.execute("SELECT promotion_name from promotions WHERE promotion_name=:promotion_name and user_id=:user_id",
            promotion_name=promo_name, user_id=session['user_id'])

            # Check to see if the user entered a promotion name that already exists
            if len(result) == 1:
                flash(promo_name + " already exists!", "danger")
                return render_template("new-promotion.html")

            start_date=request.form.get("start-date")

            # Check to see if the start date is after the end date
            if start_date >= request.form.get("end-date"):
                flash("End date must be after start date!", "danger")
                return render_template("new-promotion.html")

            # Insert the new promotion into the database and flash a message that lets the user know the promotion has been created
            db.execute("INSERT INTO promotions(promotion_name, start_date, end_date, purchase_number, reward, user_id) VALUES(?,?,?,?,?,?)",
            request.form.get("promotion-name"), request.form.get("start-date"), request.form.get("end-date"), request.form.get("reward-number"),
            request.form.get("rewards"), session["user_id"])

            flash(request.form.get("promotion-name") + " has been created!", "success")
            return redirect(url_for('homepage'))
        else:
            return render_template("new-promotion.html")

@app.route("/view-more/<promoname>", methods=["GET", "POST"])
def viewmore(promoname):
    if not session:
        return redirect(url_for('login'))
    else:
        if request.method=="POST":

            # For when the user tries to add a customer
            if not request.form.get("promo-name"):

                customer_email = request.form.get("customer-email")

                # Check to see if "customer email" and "confirm email" match
                if customer_email != request.form.get("confirm-email"):
                    flash("Emails do not match!", 'danger')
                    return redirect(request.form.get("promo-name2"))

                # Get the promotion id and name for this promotion and store it in the variables "promo_id" and "promo_name"
                query=db.execute("SELECT promotion_id, promotion_name FROM promotions WHERE promotion_name=:promotion_name AND user_id=:user_id",
                promotion_name=request.form.get("promo-name2"), user_id=session['user_id'])

                promo_id=query[0]['promotion_id']
                promo_name=query[0]['promotion_name']

                # Check the database to see if the customer email entered already exists for this promotion
                result = db.execute("""SELECT customer_email FROM customers WHERE promotion_id=:promotion_id AND customer_email=:customer_email
                AND user_id=:user_id""", promotion_id=promo_id, customer_email=customer_email, user_id=session['user_id'])

                # If customer email already exists, flash an error message and return to the view-more/<promotion_name> page
                if len(result) != 0:
                    flash(customer_email + " already exists for this promotion!", "danger")
                    return redirect(request.form.get("promo-name2"))

                # Make sure the email address is valid by checking if it contains '@' and '.com'
                if "@" not in customer_email:
                    flash(customer_email + " is not a valid email address!", "danger")
                    return redirect(request.form.get("promo-name2"))
                elif '.com' not in customer_email:
                    flash(customer_email + " is not a valid email address!", "danger")
                    return redirect(request.form.get("promo-name2"))

                # If customer email does not already exist and it is a valid email, insert the email into the database
                db.execute("INSERT INTO customers(customer_name, customer_email, user_id, promotion_id) VALUES(?,?,?,?)",
                request.form.get("customer-name"), customer_email, session["user_id"], promo_id)

                # Check to see if this customer has any previous transactions
                customer_selection = db.execute("SELECT customer_email from transactions WHERE customer_email=:customer_email AND user_id=:user_id",
                customer_email=customer_email, user_id=session["user_id"])

                # If customer does not have any previous transactions, add one to the transactions database (the purchase amount will be 0)
                if len(customer_selection) == 0:
                    transaction_time=(datetime.now(tz=pytz.UTC)).replace(microsecond=0)
                    transaction_time_eastern=transaction_time.astimezone(pytz.timezone('US/Eastern'))

                    db.execute("INSERT INTO transactions (customer_email, purchase_amount, transaction_time, user_id) VALUES(?,?,?,?)",
                    customer_email, 0, transaction_time_eastern, session['user_id'])

                # Flash message the lets the user know the customer has been added to the database and return to the view-more/<promotion_name> page
                flash(request.form.get("customer-name") + " has been added to " + promo_name + "!", "success")
                return redirect(request.form.get("promo-name2"))

            # For when the user hits "view" on the homepage
            else:
                promoname=request.form.get("promo-name")
                return redirect(promoname)
        else:
            # Get all promotion names from the database that the user has created
            result = db.execute("SELECT promotion_name FROM promotions WHERE user_id=:user_id", user_id=session['user_id'])

            # Check URL to see if it matches any of the promotion names that the user created
            for item in range(len(result)):
                if result[item]["promotion_name"]==promoname:

                    # Get the promtion id, start date, and end date from database
                    promotion_data=db.execute("""SELECT promotion_id, start_date, end_date FROM promotions WHERE promotion_name=:promotion_name
                    AND user_id=:user_id""", promotion_name=promoname, user_id=session['user_id'])

                    # Store the id and start date in variables
                    promo_id=promotion_data[0]['promotion_id']
                    start_date=promotion_data[0]['start_date']

                    # Get all the transaction times, and purchase amounts for the promotion that were transacted on or after the start date for the
                    # promotion. Only get the transaction info for the current month.
                    transactions = db.execute("""SELECT strftime('%m-%d', transaction_time), sum(purchase_amount) FROM transactions INNER JOIN customers
                    ON transactions.customer_email=customers.customer_email WHERE promotion_id=:promotion_id AND transactions.user_id=:user_id AND
                    strftime('%m',transaction_time) = strftime('%m','now') AND transaction_time >=:start_date GROUP BY strftime('%d',transaction_time)""",
                    promotion_id=promo_id, user_id=session['user_id'], start_date=start_date)

                    # Record the transaction total. If 0, the HTML won't show the graph.
                    if len(transactions) == 0:
                        transaction_total = 0
                    else:
                        transaction_total = transactions[0]["sum(purchase_amount)"]

                    # Create 2 lists, one for x-axis and one for y-axis
                    dev_x=[]
                    dev_y=[]

                    # Add all the transaction days to the dev_x list and add the total amount of sales for each day to the dev_y list
                    for transaction in transactions:
                        dev_x.append(transaction["strftime('%m-%d', transaction_time)"])
                        dev_y.append(transaction["sum(purchase_amount)"])

                    # Clear previous plot
                    plt.clf()

                    # Format plot marker and color
                    fig, ax = plt.subplots()
                    ax.plot(dev_x, dev_y, marker='o', color='#0abfaf')

                    # Set y-axis format to $0.00
                    formatter = ticker.FormatStrFormatter('$%1.2f')

                    ax.yaxis.set_major_formatter(formatter)

                    # Add x-axis and y-axis labels
                    plt.xlabel("Date")
                    plt.ylabel("Revenue")

                    # Add plot title
                    plt.title("Revenue for " + datetime.now().strftime("%B %Y"))

                    # Format x-axis so dates fit better (they are lined up diagonally)
                    plt.gcf().autofmt_xdate()

                    # Save plot as PNG
                    plt.savefig("static/plot.png", bbox_inches = 'tight')

                    # Get all customer names, customer emails, total amount they've spent, and total purcahses they've made for the specified promotion.
                    # If the transaction time of a sale for any customer is before the start date of the promotion, mark the transaction amount as $0 and
                    # don't count it as a transaction for this promotion.
                    customer_list=db.execute("""SELECT customer_name, customers.customer_email,
                    CASE
                        WHEN transaction_time >=:start_date THEN sum(purchase_amount)
                        ELSE 0
                    END AS purchase_amount,

                    CASE
                        WHEN transaction_time >=:start_date THEN count(transactions.customer_email) - 1
                        ELSE 0
                    END AS transactions

                    FROM transactions INNER JOIN customers ON customers.customer_email=transactions.customer_email
                    INNER JOIN promotions ON promotions.promotion_id=customers.promotion_id
                    WHERE promotions.promotion_id =:promotion_id AND transactions.user_id=:user_id
                    GROUP BY transactions.customer_email""",
                    start_date=start_date, promotion_id=promo_id, user_id=session['user_id'])

                    return render_template("view-more.html", promoname=promoname, promotion_data=promotion_data, customer_list=customer_list,
                    transactions=transactions, transaction_total=transaction_total)

            # If URL doesn't match any promotion name, return the homepage
            return redirect(url_for('homepage'))


@app.route("/enter-sale", methods=["GET", "POST"])
def enter_sale():
    if not session:
        return redirect(url_for('login'))

    if request.method=="GET":
        promo_names=db.execute("SELECT promotion_name FROM promotions WHERE user_id=:user_id", user_id=session["user_id"])
        customer_emails=db.execute("SELECT customer_email FROM customers WHERE user_id=:user_id GROUP BY customer_email", user_id=session["user_id"])

        return render_template("enter-sale.html", promo_names=promo_names, customer_emails=customer_emails)
    else:
        # Get the customer email that was entered
        customer_email=request.form.get("customer-email-list")

        # Check if the customer email entered exists in the database
        customer_name = db.execute("SELECT customer_name FROM customers WHERE customer_email=:customer_email AND user_id=:user_id",
        customer_email=customer_email, user_id=session["user_id"])

        # If it doesn't exist flash an error message and redirect to the enter-sale page
        if len(customer_name) == 0:
            flash("Customer email does not exist!", 'danger')
            return redirect("/enter-sale")

        # Store customer name in variable
        customer_name=customer_name[0]['customer_name']

        # Get the current time from the Eastern timezone
        transaction_time=(datetime.now(tz=pytz.UTC)).replace(microsecond=0)
        transaction_time_eastern=transaction_time.astimezone(pytz.timezone('US/Eastern'))

        # Insert the transaction into the database
        db.execute("INSERT INTO transactions (customer_email, purchase_amount, transaction_time, user_id) VALUES(?,?,?,?)",
        customer_email, request.form.get("sale-price"), transaction_time_eastern, session['user_id'])

        # Flash message that the sale was recorded
        flash("Sale for " + customer_email + " has been recorded!", 'success')

        # Get the total number of purchases made by the customer and store it in a variable called 'purcahses'
        # (we must subtract 1 bc we automatically create a transaction when the customer is created)
        result = db.execute("""SELECT count(customer_email) FROM transactions WHERE customer_email=:customer_email AND user_id=:user_id
        GROUP BY customer_email""", customer_email=customer_email, user_id=session["user_id"])

        purchases = result[0]['count(customer_email)'] - 1

        # Select the purchase number and reward from all promotions that the customer is signed up for. Only select the promotions that have already started
        promo_information = db.execute("""SELECT purchase_number, reward FROM promotions INNER JOIN customers ON
        promotions.promotion_id=customers.promotion_id WHERE customer_email=:customer_email AND customers.user_id=:user_id
        AND start_date <=:transaction_time_eastern""",
        customer_email=customer_email, user_id=session['user_id'], transaction_time_eastern=transaction_time_eastern)

        # Loop through all the promotions and if the remainder is 0 when we divide the total purchases of the customer by the number of purchases needed to
        # win a reward, flash a message letting them know that the customer has won a reward
        if len(promo_information) > 0:
            for item in promo_information:
                if purchases%item["purchase_number"] == 0:
                    flash(customer_name + " has been rewarded: " + item['reward'] + '!', 'warning')

        return redirect("/enter-sale")

@app.route("/delete", methods=["POST"])
def delete():
    promotion_name=request.form.get("promo-name3")

    # Get the promotion ID for the promotion that the user has requested to delete and store it in a variable called promo_id
    result = db.execute("SELECT promotion_id FROM promotions WHERE promotion_name=:promotion_name AND user_id=:user_id", promotion_name=promotion_name,
    user_id=session['user_id'])

    promo_id=result[0]["promotion_id"]

    # Delete all the customers associated with that promotion and then delete the promotion itself from the database
    db.execute("DELETE FROM customers WHERE promotion_id=:promotion_id AND user_id=:user_id", promotion_id=promo_id, user_id=session['user_id'])
    db.execute("DELETE FROM promotions WHERE promotion_id=:promotion_id AND user_id=:user_id", promotion_id=promo_id, user_id=session['user_id'])

    # Flash a message saying the promotion was deleted and redirect to the homepage
    flash(promotion_name + " has been successfuly deleted!", "success")
    return redirect("/homepage")
