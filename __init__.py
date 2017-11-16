from flask import Flask
from flask import render_template, request, send_from_directory
from flask.ext.bootstrap import Bootstrap
import records
import datetime

#
app = Flask(__name__)
bootstrap = Bootstrap(app)


# --- connect to database
db_host = '127.0.0.1'
db_usr = 'root'
db_pwd = 'wave'
db_type = 'mysql'
db_name = 'DB_MOUNTS'
db_url = db_type + '://' + db_usr + ':' + db_pwd + '@' + db_host + '/' + db_name
dbo = records.Database(db_url)


# === define routes

@app.route('/')
def index():
    return render_template("home.html")


@app.route("/home")
def home():
    return render_template("home.html")


@app.route('/targets')
def get_targets():

    stmt = "SELECT * FROM DB_MOUNTS.targets"
    rows = dbo.query(stmt)

    return render_template("targets.html", targets=rows)


@app.route('/stats/<id>')
def stats(id):
    stmt = "SELECT * FROM DB_MOUNTS.results_img WHERE target_id = '" + id + "'"

    rows = dbo.query(stmt)

    return render_template("stats.html", results=rows)


@app.route("/about")
def about():
    return render_template("about.html")


@app.route("/debug")
def debug():
    return "Berlin!"


@app.route("/volcano/<id>")
def volcano(id):

    # --- get target information (display in table)
    stmt = "SELECT * FROM DB_MOUNTS.targets WHERE id = '" + id + "'"
    tgt_stats = dbo.query(stmt)

    # --- get target results (ifg+coh)
    q = '''
        SELECT R.title, R.abspath, R.type, A.acqstarttime
        FROM results_img AS R
        INNER JOIN archive AS A
        ON R.id_master = A.id
        WHERE R.target_id = {} AND R.type = 'ifg' OR R.type = 'coh'
        ORDER BY A.acqstarttime desc
        '''
    stmt = q.format(id)
    imgS1 = dbo.query(stmt)

    # --- get target results (ifg+coh)
    q = '''
        SELECT R.title, R.abspath, R.type, A.acqstarttime
        FROM results_img AS R
        INNER JOIN archive AS A
        ON R.id_master = A.id
        WHERE R.target_id = {} AND R.type = 'nir'
        ORDER BY A.acqstarttime desc
        '''
    stmt = q.format(id)
    imgS2 = dbo.query(stmt)

    return render_template("volcano.html", imgS1=imgS1, imgS2=imgS2, tgt_stats=tgt_stats[0])


# === define additional jinja filters
def int2td(value, unit='days'):
    '''Convert integer value to timedelta object.'''
    if unit == 'days':
        timedelta = datetime.timedelta(days=value)
    elif unit == 'hours':
        timedelta = datetime.timedelta(hours=value)
    elif unit == 'minutes':
        timedelta = datetime.timedelta(minutes=value)

    return timedelta


def td2int(value, unit='days'):
    '''Convert timedelta object to integer'''
    if unit == 'days':
        timedelta_int = value.total_seconds() / (3600 * 24)
    elif unit == 'hours':
        timedelta_int = value.total_seconds() / 3600
    elif unit == 'minutes':
        timedelta_int = value.total_seconds() / 60

    return timedelta_int


app.jinja_env.filters['int2td'] = int2td
app.jinja_env.filters['td2int'] = td2int


# === in development
html = '''
<html>
    <body>
        <img src="data:image/png;base64,{}" />
    </body>
</html>
'''


@app.route("/plot")
def plot():
    import matplotlib
    matplotlib.use('Agg')

    import matplotlib.pyplot as plt
    import numpy as np
    import pandas as pd
    from cStringIO import StringIO
    import base64

    df = pd.DataFrame(
        {'y': np.random.randn(10), 'z': np.random.randn(10)},
        index=pd.period_range('1-2000', periods=10),
    )
    fig = plt.figure()
    ax = fig.add_subplot(1, 1, 1)
    df.plot(ax=ax)

    io = StringIO()
    fig.savefig(io, format='png')
    data = base64.encodestring(io.getvalue())

    return html.format(data)


if __name__ == "__main__":
    app.run()
