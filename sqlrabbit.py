import pystache
from flask import Flask,session,redirect,url_for,send_from_directory,request,g
import MySQLdb
import MySQLdb.cursors
import json
import logging
log = logging.getLogger('werkzeug')
log.setLevel(logging.ERROR)
from utils import *

app = Flask(__name__)
app.secret_key = 'sdh'

nav_copy_fields=['sort', 'database', 'query', 'table', 'dir']
max_rows=10

def get_connection(connp):
    try:
        mydb = MySQLdb.connect(cursorclass=MySQLdb.cursors.DictCursor,**connp)
        return mydb,None
    except Exception as ex:
        return None,str(ex)

def print_title(s):
    return '<td class=heading>'+str(s)+'</td>\n'

def param_one_of(value,values):
	if value in values:
		return value
	return values[0]

def param_toggle(val,vals):
    return vals[1] if val==vals[0] else vals[0]

def print_sort_title(field):
    if p('sort') == field:
        dir_values = ['asc', 'desc']
        dir = param_one_of(p('dir'), dir_values)
        other_dir = param_toggle(p('dir'),dir_values)
        href = make_url({'dir':other_dir},nav_copy_fields);
        img = '<img src=/media/'+dir+'.png>'
        return('<td class=heading id='+field+'><a href='+href+'>'+field+'  '+img+'</a></td>\n');
    else:
        link = make_link(field,{'sort':field,'dir':'asc'}, nav_copy_fields)
        return '<td class=heading id='+field+'>'+link+'</td>\n'

def print_last_line(num_fields,no_rows_at_all):
    ans=print_title("*")
    ans+='<td colspan='+str(num_fields)+'><b>'
    if no_rows_at_all:
        ans+="(There are no rows in this table)"
    else:
        ans+="(There are no more rows)"
    ans+="</b></td>\n"
    return ans

def decorate(val):
    if val is None:
        return "<span class=ns>null</span>"
    if val is True or val is False:
        return '<span class=ns>'+val+'</span>'
    return val

def print_val_td(val):
    return '<td>'+decorate(str(val))+'</td>'

def print_next_prev(print_next):
    def print_link(title,should_print,start):
        if should_print:
            return make_link(title,{'start':start},nav_copy_fields)
        else:
            return title
    start=pint('start')
    return print_link('Last',start >= max_rows,start-max_rows)+"&nbsp;&nbsp;&nbsp; |&nbsp;&nbsp;&nbsp"+print_link('Next',print_next,start+max_rows)

def print_table_title(fields):
    buf='<tr>'+print_title("   ");
    for field in fields:
        buf+=print_sort_title(field)
    buf+="</tr>";
    return buf

def print_row(row,oridnal,fields,first_col):
    buf="<tr>\n"
    buf += print_title(oridnal)
    for j,field in enumerate(fields):
        val=row[field]
        if j == 0 and first_col:
            val = first_col(val)
        buf+=print_val_td(val)
    buf+="</tr>"            
    return buf

def make_result(body,fields,print_next,lastline=''):
    table="\n<table id=data>"+print_table_title(fields)+body+lastline+'</table>\n'
    return {
        'nextprev':print_next_prev(print_next),
        'query_result':table
    }

def mem_print_table(view,results, fields):
    if p('sort'):
        results=sorted(results,key=lambda k: k[p('sort')],reverse=p('dir')=='desc')
    buf=''
    if view.show_cols:
        fields=[field for i,field in enumerate(fields) if i in view.show_cols]
    start=pint('start')
    for i in xrange(start,start+max_rows):
        if i >= len(results):
            return make_result(buf,fields,False,print_last_line(len(fields),i==0))
        buf+=print_row(results[i],i+1,fields,view.first_col)
    return make_result(buf,fields,True)

def result_print_table(view,results, fields):
    buf=''
    for i in xrange(0,max_rows):
        if i >= len(results):
            return make_result(buf,fields,False,print_last_line(len(fields),i==0))
        buf+=print_row(results[i],i+1+pint('start'),fields,view.first_col)
    return make_result(buf,fields,True)

def decorate_database_name(val):
    return make_link(val,{'database':val,'endpoint':'database'})

def decorate_table_name(val):
    return make_link(val,{'table':val,'endpoint':'table'},['database'])

def read_connp():
    def read_from_cookie():
        try:
            session_val=session['connp']
            ans=json.loads(session_val)
            return ans  
        except Exception as ex:
            return {}# 'host': 'localhost', 'user': 'guest', 'passwd': 'guest' }
    ans = read_from_cookie()
    ans['db'] = p('database')
    ans = pick(ans, 'host', 'user', 'passwd', 'db');
    return ans

def save_connp(p):
    connp = pick(p, 'host', 'user', 'passwd');
    session['connp']=json.dumps(connp)

def query_and_send(view):
    def calc_view2(results,fields,error):
        if error:
            return {'query_error': error}
        if fields is None:
            return { 'ok': 'query completed succesfuly' }
        return view.printer(view,results, fields);
    def execute_and_send(connection):
        view.query_edit_href=make_url({'query':view.query,'database':p('database'),'endpoint':'query'})
        query=view.query+(view.query_decoration or '')
        error,results,fields =myquery2(connection,query)
        view2 = calc_view2(results, fields, error);
        view.logout_href=make_url({'endpoint':'logout'})
        view.conn_p = read_connp();
        ans=render('templates/template.htm', view,view2)
        connection.close()
        return ans
    connection,error=get_connection(read_connp())
    if (error):
        return redirect(url_for('login'), code=302)
    return execute_and_send(connection)

def databases_link():
    return make_link('databases',{'endpoint':'databases'})

def print_switch(table_class, schema_class):
    data_ref = make_url({'endpoint':'table'},['database','table'])
    schema_href =make_url({'endpoint':'table_schema'}, ['database', 'table'])
    return '(  <a '+table_class+' href='+data_ref+'>Data</a> | <a '+schema_class+' href='+schema_href+'>Schema</a> )'

def calc_query_decoration():
    p=g.args
    ans='';
    if p.sort:
        ans+=' order by '+p.sort+' '+p.dir+' ';
    ans+=' limit '+str(pint('start'))+', '+str(max_rows);
    return ans

@app.before_request
def before_request():
    g.args=calc_args()


@app.route('/media/<path:path>')
def send_js(path):
    return send_from_directory('media', path)

@app.route('/favicon.ico')
def favicon():
    return send_from_directory('media', 'favicon.ico')

@app.route('/login_submit',methods=['POST','GET'])
def login_submit():
    save_connp(g.args)
    connection,error=get_connection(read_connp()); 
    if error:
       return render('templates/login_template.htm', g.args, { 'error': error }) 
    else:
       return redirect('/',code=302)


@app.route('/logout')
def logout():
    session['connp']=None
    return redirect('/', code=302)

@app.route('/login')
def login():
    return render('templates/login_template.htm',{})

@app.route('/')
@app.route('/databases')
def databases():
    view=DDict(
        about='The table below shows all the databases that are accessible in this server: Click on any database below to browse it',
        title='show databases',
        query='show databases',
        printer=mem_print_table,
        first_col=decorate_database_name
    )     
    return query_and_send(view)

@app.route('/database/<database>')
def database(database):
    p=g.args
    view=DDict(
        about= 'The table below shows all the available tables in the database '+database+', Click on any table below to browse it',
        title= 'show database '+database,
        query= 'show table status',
        navbar= databases_link()+" / "+database,
        printer=mem_print_table,
        first_col=decorate_table_name,
        show_cols=[0, 1, 4, 17]
    )
    return query_and_send(view)

@app.route('/table/<database>/<table>')
def table(database,table):
    p=g.args
    view=DDict(
        about='The table below shows the table '+p.table+', you can select either schema or data view',
        view_options=print_switch('class=selected', ''),
        title= p.database+' / ' +p.table,
        query= 'select * from '+p.table,
        navbar=databases_link()+' / '+decorate_database_name(p.database)+' / '+p.table,
        query_decoration= calc_query_decoration(),
        printer=result_print_table
    )
    return query_and_send(view)

@app.route('/table_schema/<table>')
def table_schema(table):
    p=g.args
    view=DDict(
        about= 'The table below shows the table '+p.table+', you can select either schema or data view',
        view_options= print_switch('', 'class=selected'),
        query='describe '+p.table,
        navbar=databases_link()+" / "+decorate_database_name(p.database)+' / '+p.table,
        printer=mem_print_table
    )
    return query_and_send(view)

@app.route('/query')
def query():
    p=g.args
    view=DDict(
        about='Enter any sql query'+(' for database '+p.database if p.database else ''),
        title='User query',
        query=p.query,
        querytext=p.query,
        navbar=databases_link()+('/' + decorate_database_name(p.database) if p.database else'')+' / query',
        printer=result_print_table
    )
    if (p.query.startswith('select')):
        view.query_decoration=calc_query_decoration()
    return query_and_send(view)

if __name__ == "__main__":
    app.run(threaded=True,debug=False)