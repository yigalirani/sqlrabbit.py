import pystache
from flask import request,url_for,g
class DDict(dict):
    def __getattr__(self, attr):
        return self.get(attr,'')

    def __setattr__(self, key, value):
        self.__setitem__(key, value)
def calc_args():
    ans=DDict()
    ans.endpoint=get_endpoint()
    for d in [request.args,request.view_args]:
        for key,value in d.iteritems():
            ans[key]=value
    return ans
def make_url(args={},copy_fields=[]):
    new_args={}
    for x in copy_fields:
        new_args[x]=g.args.get(x,None)
    for name,value in args.iteritems():
        new_args[name]=value
    if 'endpoint' not in new_args:
        endpoint=g.args.endpoint
    else:
        endpoint=new_args['endpoint']
        del new_args['endpoint']
    return url_for(endpoint,**new_args)

def make_link(text,args={},copy_fields=[]):
	return '<a href="'+make_url(args,copy_fields)+'">'+text+'</a>'

def p(name):
    return g.args.get(name,'')## that means that non-existant is returned as empty string
def pint(name):
    try:
        return int(p(name))
    except ValueError:
        return 0
def get_endpoint():
    if request.url_rule:
        return request.url_rule.endpoint
    return None
def render(file,data,date2={},date3={}):
    merged={}
    merged.update(data)
    merged.update(date2)
    merged.update(date3)
    renderer = pystache.Renderer(file_encoding='UTF8')
    ans=renderer.render_path(file, merged)
    return ans

def myquery2(db,sql):
	try:
		with db as cursor: 
			cursor.execute(sql)
			if cursor.description is None:
				return None,cursor,None
			return None,cursor.fetchall(),[x[0] for x in cursor.description]
	except Exception as ex:
		return str(ex.args[1]),None,None,
def pick(dict,*keys):
    ans= { key: dict.get(key,None) for key in keys}
    return ans
