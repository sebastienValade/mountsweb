from flask import Flask
from flask import render_template, request, send_from_directory
from flask.ext.bootstrap import Bootstrap
import records
import datetime
import pandas as pd
import json
import plotly
import plotly.graph_objs as go
from sqlalchemy import create_engine  # database connection
import numpy as np

app = Flask(__name__)
bootstrap = Bootstrap(app)


# --- connect to database
db_host = '127.0.0.1'
db_usr = 'root'
db_pwd = 'br12Fol!'
db_type = 'mysql'
db_name = 'DB_MOUNTS'
db_url = db_type + '://' + db_usr + ':' + db_pwd + '@' + db_host + '/' + db_name
dbo = records.Database(db_url)


disk_engine = create_engine(db_url)

# === define routes


@app.route('/')
def index():
    return render_template("home.html")


@app.route("/home")
def home():
    return render_template("home.html")


@app.route('/targets')
def get_targets():

    stmt = "SELECT fullname, id FROM DB_MOUNTS.targets ORDER BY fullname"
    rows = dbo.query(stmt)

    return render_template("targets.html", targets=rows)


@app.route('/earthquakes')
def earthquakes():

    return render_template("earthquakes.html")


@app.route("/about")
def about():
    return render_template("about.html")


@app.route("/volcano/<id>")
def volcano(id):
    # => logic made here with pandas libraries to grouby (rather with jinja2 templates)

    # --- get target information (display in table)
    stmt = "SELECT * FROM DB_MOUNTS.targets WHERE id = '" + id + "'"
    tgt_stats = dbo.query(stmt)

    # --- get target s1 results (ifg+coh+int)
    q = '''
        SELECT R.title, R.abspath, R.type, S.acqstarttime AS acqstarttime_slave, M.acqstarttime AS acqstarttime_master
        FROM results_img AS R
        INNER JOIN archive AS S ON R.id_slave = S.id
        INNER JOIN archive AS M ON R.id_master = M.id
        WHERE R.target_id = {} AND S.acqstarttime > '2017-01-01' AND (R.type = 'ifg' OR R.type = 'coh' OR R.type = 'int_VV')
        ORDER BY S.acqstarttime desc, R.type desc
    '''
    stmt = q.format(id)
    df_S1 = pd.read_sql(stmt, disk_engine)

    # --- get target s2 results (nir)
    q = '''
        SELECT R.title, R.abspath, R.type, S.acqstarttime AS acqstarttime_slave, M.acqstarttime AS acqstarttime_master
        FROM results_img AS R
        INNER JOIN archive AS S ON R.id_slave = S.id
        INNER JOIN archive AS M ON R.id_master = M.id
        WHERE R.target_id = {} AND R.type = 'nir'
        ORDER BY M.acqstarttime desc
    '''
    stmt = q.format(id)
    df_S2 = pd.read_sql(stmt, disk_engine)

    # --- group S1 dataframe by slave image acquisition date
    gb = df_S1.groupby('acqstarttime_slave', sort=False)

    img_groups = []
    for group_name, group in gb:

        # - search for closest S2 image to group date, and append
        idx = np.argmin(abs(group_name - df_S2.acqstarttime_master))
        group = group.append(df_S2.iloc[idx], ignore_index=True)

        # - store group as dictionary
        group_dict = group.to_dict('list')
        group_dict['groupdate'] = group_name    # => field stores group date (timestamp)
        group_dict['dt'] = df_S2.iloc[idx]['acqstarttime_master'] - group_name  # => field stores delta t between group date and selected S2 img
        img_groups.append(group_dict)

    return render_template("volcano.html", img_groups=img_groups, tgt_stats=tgt_stats[0])


@app.route("/volcano_old/<id>")
def volcano_old(id):
    # => uses jinja2 template to grouby

    # --- get target information (display in table)
    stmt = "SELECT * FROM DB_MOUNTS.targets WHERE id = '" + id + "'"
    tgt_stats = dbo.query(stmt)

    # --- get target s1 results (ifg+coh)
    q = '''
        SELECT R.title, R.abspath, R.type, A.acqstarttime
        FROM results_img AS R
        INNER JOIN archive AS A
        ON R.id_slave = A.id
        WHERE R.target_id = {} AND A.acqstarttime > '2017-01-01' AND (R.type = 'ifg' OR R.type = 'coh' OR R.type = 'int_VV')
        ORDER BY A.acqstarttime, R.type desc
        '''
    stmt = q.format(id)
    imgS1 = dbo.query(stmt)

    # --- get target s2 results (nir)
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

    return render_template("volcano_old.html", imgS1=imgS1, imgS2=imgS2, tgt_stats=tgt_stats[0])


@app.route("/volcano_tmp/<id>")
def volcano_tmp(id):

    # --- get target information (display in table)
    stmt = "SELECT * FROM DB_MOUNTS.targets WHERE id = '" + id + "'"
    tgt_stats = dbo.query(stmt)

    q = '''
        SELECT R.title, R.abspath, R.type, S.acqstarttime AS acqstarttime_slave, M.acqstarttime AS acqstarttime_master
        FROM results_img AS R
        INNER JOIN archive AS S ON R.id_slave = S.id
        INNER JOIN archive AS M ON R.id_master = M.id
        WHERE R.target_id = {} AND S.acqstarttime > '2017-01-01' AND (R.type = 'ifg' OR R.type = 'coh' OR R.type = 'int_VV')
        ORDER BY S.acqstarttime desc, R.type desc
    '''
    stmt = q.format(id)
    df_S1 = pd.read_sql(stmt, disk_engine)

    # --- get target s2 results (nir)
    q = '''
        SELECT R.title, R.abspath, R.type, M.acqstarttime AS acqstarttime_master
        FROM results_img AS R
        INNER JOIN archive AS M
        ON R.id_master = M.id
        WHERE R.target_id = {} AND R.type = 'nir'
        ORDER BY M.acqstarttime desc
        '''
    stmt = q.format(id)
    df_S2 = pd.read_sql(stmt, disk_engine)

    gb = df_S1.groupby('acqstarttime_slave', sort=False)

    import numpy as np
    idx = [np.argmin(abs(i - df_S2.acqstarttime_master)) for i in sorted(gb.groups.iterkeys(), reverse=True)]
    imgS2 = df_S2.iloc[idx]

    return render_template("volcano_tmp.html", imgS1=gb, imgS2=imgS2, tgt_stats=tgt_stats[0])


@app.route("/timeseries/<id>")
def timeseries(id):

    # --- get target information (display in table)
    stmt = "SELECT * FROM DB_MOUNTS.targets WHERE id = '" + id + "'"
    tgt_stats = dbo.query(stmt)                 # =>  name = tgt_stats[0].name
    # tgt_stats = pd.read_sql(stmt, disk_engine)  # =>  name = tgt_stats.name[0]

    # --- get data in database (pandas/sqlalchemy)
    # TODO: make a unique query and filter result
    stmt = "SELECT time, data FROM DB_MOUNTS.results_dat WHERE type='coh' ORDER BY time ASC"
    df = pd.read_sql(stmt, disk_engine)

    stmt = "SELECT time, data FROM DB_MOUNTS.results_dat WHERE type='nir' ORDER BY time ASC"
    df_nir = pd.read_sql(stmt, disk_engine)

    # --- plot (pandas)
    # df.plot(x='time', y='data')
    # plt.show()

    # -- create the plotly data structure
    trace1 = go.Scatter(
        x=df["time"],
        y=df["data"],
        name="coh",
        mode='lines+markers'
    )
    trace2 = go.Scatter(
        x=df_nir["time"],
        y=df_nir["data"],
        name="nir",
        mode='lines+markers',
        yaxis='y2'
    )

    ti = datetime.datetime.strptime("2017-01-01", "%Y-%m-%d")
    tf = min(df["time"].iloc[-1], df_nir["time"].iloc[-1])
    graph = dict(
        data=[trace1, trace2],
        layout=dict(
            xaxis=dict(range=[ti, tf]),
            yaxis=dict(title="index of change"),
            yaxis2=dict(title="infrared", overlaying='y', anchor='y', side='right', zeroline=False),
            showlegend=True
        )
    )

    # --- convert the figures to JSON
    graphJSON = json.dumps(graph, cls=plotly.utils.PlotlyJSONEncoder)

    return render_template('timeseries.html', graphJSON=graphJSON, tgt_stats=tgt_stats[0])


@app.route("/plot_tmp")
def plot_tmp():
    # --- get data in database
    stmt = "SELECT time, data FROM DB_MOUNTS.results_dat WHERE type='coh' ORDER BY time ASC"
    rows = dbo.query(stmt)
    dat = rows.dataset
    t_str = dat.get_col(0)
    print t_str
    # t_datetime = pd.to_datetime(t_str)
    t_datetime = [datetime.datetime.strptime(t, "%Y-%m-%dT%H:%M:%S") for t in t_str]
    y = dat.get_col(1)

    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    import numpy as np
    from cStringIO import StringIO
    import base64

    df = pd.DataFrame(
        {'x': t_datetime, 'y': y},
    )
    fig = plt.figure()
    ax = fig.add_subplot(1, 1, 1)

    # plt.plot(t_datetime, y)
    # plt.xticks(rotation=10)
    # plt.draw()

    df.plot(ax=ax)

    io = StringIO()
    fig.savefig(io, format='png')
    data = base64.encodestring(io.getvalue())

    return html.format(data)


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


@app.route("/plot_static")
def plot_static():
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
