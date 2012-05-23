"""
# Geodata

Export geo location data from the recent_changes table. The script is running multiple languages in parallel. For each language it does the following steps.

1. Export the recent_changes tables to avoid doing analytics on a production server
2. Exract/Transform/Load on exported data

"""

import os
from multiprocessing import Pool
import logging
logging.basicConfig(level=logging.INFO)


# if only we could use a mysql driver....
try:
    import MySQLdb,MySQLdb.cursors
except:
    logging.warning("Warning: SQL module MySQLdb could not be imported.")

import geo_coding as gc
import languages
import mysql_config

data_dir = './data'
output_dir = './output'


def mysql_resultset(lang):

	host_name = mysql_config.get_host_name(lang)
	db_name = mysql_config.get_db_name(lang)

	# mysql query to export recent changes data
	# query = mysql_config.construct_rc_query(db_name)
	query = mysql_config.construct_cu_query(db_name,'201204')

	logging.info("SQL query for %s:\n\t%s"%(db_name,query))

	db = MySQLdb.connect(host=host_name,read_default_file=os.path.expanduser('~/.my.cnf'))
	SScur = db.cursor(MySQLdb.cursors.SSCursor)

	logging.info('Connected to [db:%s,host:%s]'%(db_name,host_name))

	SScur.execute(query)

	return SScur


def dump_data_iterator(lang,compressed=False):
	'''Dumps the needed entries from the recent changes table for language lang.

	:returns: Iterable open file object 
	'''

	host_name = mysql_config.get_host_name(lang)
	db_name = mysql_config.get_db_name(lang)
	# user_name = mysql_config.user_name
	# pw = mysql_config.password

	
	# mysql query to export recent changes data
	query = mysql_config.recentchanges_query%db_name


	if compressed:
		output_fn = os.path.join(data_dir,'%s_geo.tsv.gz'%lang)	
		# export_command = ['mysql', '-h', host_name,  '-u%s'%user_name,  '-p%s'%pw ,'-e', "'%s'"%query, '|', 'gzip', '-c' ,'>', output_fn]
		export_command = ['mysql', '-h', host_name ,'-e', "'%s'"%query, '|', 'gzip', '-c' ,'>', output_fn]

	else:
		output_fn = os.path.join(data_dir,'%s_geo.tsv'%lang)		
		# export_command = ['mysql', '-h', host_name,  '-u%s'%user_name,  '-p%s'%pw ,'-e', "'%s'"%query, '>', output_fn]
		export_command = ['mysql', '-h', host_name ,'-e', "'%s'"%query, '>', output_fn]



	# use problematic os.system instead of subprocess
	os.system(' '.join(export_command))	


	if compressed:
		source =  gzip.open(output_fn, 'r')
	else:
		source =  open(output_fn, 'r')

	# discard the headers!
	source.readline()

	return source



def create_dataset(lang):

	logging.info('CREATING DATASET FOR %s'%lang)

	# EXTRACT

	### export the data from mysql by dumping into a temp file
	# source = dump_data_iterator(lang,compressed=True)		
	# (editors,countries_cities) = gc.extract(source,sep='\t')
	
	# OR

	### use a server-side cursor to iterate the result set
	source = mysql_resultset(lang)
	(editors,cities) = gc.extract(source)

	# TRANSFORM (only for editors)
	countries_editors,countries_cities = gc.transform(editors,cities)

	# LOAD 
	gc.load(lang,countries_editors,countries_cities,output_dir)

	# delete the exported data
	# os.system('rm %s'%fn)

	logging.info('DONE : %s'%lang)


if __name__ == '__main__':

	# check that data/output directories exist, create if not
	# todo move into an arg parser
	# if not os.path.exists(data_dir):
	# 	os.mkdir(data_dir)
	if not os.path.exists(output_dir):
		os.mkdir(output_dir)

	p = Pool(4)

	# languages = languages.languages
	languages =  ['ar','pt','hi','en']
	p.map(create_dataset, languages)
	
	# test a language for debugging
	# create_dataset('ar')	

	logging.info('All languages done. Results are in %s folder'%(output_dir))

