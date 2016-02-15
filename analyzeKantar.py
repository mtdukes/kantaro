import agate
from ftplib import FTP
import dateparser
import datetime
import os.path
import boto3

#global variables
dates = []
secret_keys = []
data_dest = 'data/'
s3 = boto3.resource('s3')

#utility function for constructing a list of 
#dates and filenames of CSVs in Kantar data
def _parse_dir(line):
	if line[-3:] == 'csv':
		dates.append([dateparser.parse(line[0:8]),line.rsplit(' ',1)[1]])

#utility function for retrieving secret keys
def _get_secrets():
	global secret_keys
	with open('.keys') as f:
		secret_keys = f.read().splitlines()

def access_kantar():
	_get_secrets()
	print 'Accessing Kantar data...'
	#attempt to log in to Kantar's FTP site
	try:
		ftp = FTP(secret_keys[5])
		ftp.login(secret_keys[4],secret_keys[2])
		ftp.cwd(secret_keys[6])
		print 'Access granted...'

		#add CSVs in the directory to date list
		ftp.dir(_parse_dir)
		#get the most recently uploaded file based on time stamp
		latest_file = sorted(dates,key=lambda date_file: date_file[0],reverse=True)[0][1]
		#check if the file is downloaded
		if os.path.exists(data_dest+latest_file):
			print 'File already downloaded...'
		else:
			file = open(data_dest + latest_file,'wb')
			ftp.retrbinary('RETR %s' % latest_file, file.write)
			print 'Latest file downloaded to',data_dest+latest_file
		ftp.quit()
		return latest_file
	except Exception, e:
		print "Error logging into Kantar:", e
		return None

#utility for shortening cell values by a pipe
def shorten(value):
	if value != None:
		value = value.lower()
		value = value.rsplit('|')[0]
		return value
	else:
		return value

def get_campaign_totals(filename):
	print "Calculating campaign totals..."
	#explicitly name rows so you can grab variables later
	ad_buys = agate.Table.from_csv(filename, row_names=lambda row:'%(CREATIVE)s' % (row))

	by_campaign = ad_buys.group_by('CREATIVE','creative')
	totals = by_campaign.aggregate([
		('total',agate.Sum('EST. COST'))
		])
	#add information 
	totals = totals.compute([
		('sponsor',agate.Formula(agate.Text(),lambda row: ad_buys.rows[row['creative']]['SPONSOR'] )),
		('ad_type',agate.Formula(agate.Text(),lambda row: ad_buys.rows[row['creative']]['AD TYPE'] )),
		('issue_short',agate.Formula(agate.Text(),lambda row: shorten(ad_buys.rows[row['creative']]['ISSUE']) )),
		('issue_long',agate.Formula(agate.Text(),lambda row: ad_buys.rows[row['creative']]['ISSUE'] )),
		('gif_url',agate.Formula(agate.Text(),lambda row: ad_buys.rows[row['creative']]['LINK'] ))
		])

	print "Campaign totals calculated..."

	totals.to_csv(data_dest+'campaign_totals.csv')
	s3.Object('mtduk.es', 'data/campaign_totals.csv').put(Body=open(data_dest+'campaign_totals.csv', 'rb'))

	print "CSV saved to",data_dest+'campaign_totals.csv','and S3'

def get_sponsor_totals(filename):
	print 'Calculating sponsor totals...'
	ad_buys = agate.Table.from_csv(filename)
	#year doesn't denote run year, so this is uneccessary
	#ad_buys = ad_buys.where(lambda row: row['YEAR'] == 2015 or row['YEAR'] == 2016)

	by_sponsor = ad_buys.group_by('SPONSOR')
	totals = by_sponsor.aggregate([
		('sponsor_cost',agate.Sum('EST. COST'))
	])
	totals = totals.order_by('sponsor_cost', reverse=True)

	print 'Sponsor totals calculated...'

	totals.to_csv(data_dest+'sponsor_totals.csv')
	s3.Object('mtduk.es', 'data/sponsor_totals.csv').put(Body=open(data_dest+'sponsor_totals.csv', 'rb'))

	print "CSV saved to",data_dest+'sponsor_totals.csv','and S3'

#This is crazy messy. Can we refactor?
def get_historical_totals(filename):
	print 'Calculating historical totals...'
	prev_Monday = _getMondayDate(datetime.date.today())
	ad_buys = agate.Table.from_csv(filename)
	#generate pivot table equivalent of grouped date columns on EST. COST by sponsor
	by_sponsor = ad_buys.group_by('SPONSOR','sponsor')
	sponsor_list = ad_buys.distinct('SPONSOR').select(('SPONSOR',))

	#calculate the week totals
	by_week = by_sponsor.group_by(
		lambda r: '%i' % ((prev_Monday-r['AIRDATE']).days // 7),
		key_name="week_period"
		)
	week_totals = by_week.aggregate([
		('sponsor_cost',agate.Sum('EST. COST')),
		('count',agate.Length())
	])
	week0 = week_totals.where(lambda row: row['week_period'] == '0')
	week1 = week_totals.where(lambda row: row['week_period'] == '1')

	#calculate the month totals
	by_month = by_sponsor.group_by(
		lambda r: '%i' % ((prev_Monday-r['AIRDATE']).days // 28),
		key_name="month_period"
		)
	month_totals = by_month.aggregate([
		('sponsor_cost',agate.Sum('EST. COST')),
		('count',agate.Length())
	])
	month0 = month_totals.where(lambda row: row['month_period'] == '0')
	month1 = month_totals.where(lambda row: row['month_period'] == '1')

	#calculate the quarter totals
	by_quarter = by_sponsor.group_by(
		lambda r: '%i' % ((prev_Monday-r['AIRDATE']).days // 91),
		key_name="quarter_period"
		)
	quarter_totals = by_quarter.aggregate([
		('sponsor_cost',agate.Sum('EST. COST')),
		('count',agate.Length())
	])
	quarter0 = quarter_totals.where(lambda row: row['quarter_period'] == '0')
	quarter1 = quarter_totals.where(lambda row: row['quarter_period'] == '1')

	#join the tables with week
	history = sponsor_list.join(week0,'SPONSOR','sponsor')
	history = history.join(week1,'SPONSOR','sponsor')
	history = history.exclude(('week_period','week_period2'))
	history = history.rename(column_names=[
		'sponsor','current_wk_cost','current_wk_count','last_wk_cost','last_wk_count'])
	history = history.compute([
		('week_raw',agate.Formula(agate.Number(),lambda row: nullRawChange(row[3],row[1]))),
		#('week_raw',agate.Change('last_wk_cost','current_wk_cost')),
		('week_pct',agate.Formula(agate.Number(),lambda row: nullPctChange(row[3],row[1]))),
		])

	#join the tables for months
	history = history.join(month0,'sponsor','sponsor')
	history = history.join(month1,'sponsor','sponsor')
	history = history.exclude(('month_period','month_period2'))
	history = history.rename(column_names=[
		'sponsor','current_wk_cost','current_wk_count','last_wk_cost','last_wk_count','week_raw','week_pct',
		'current_mth_cost','current_mth_count','last_mth_cost','last_mth_count'])
	history = history.compute([
		('month_raw',agate.Formula(agate.Number(),lambda row: nullRawChange(row[9],row[7]))),
		('month_pct',agate.Formula(agate.Number(),lambda row: nullPctChange(row[9],row[7]))),
		])

	#join the tables for quarters
	history = history.join(quarter0,'sponsor','sponsor')
	history = history.join(quarter1,'sponsor','sponsor')
	history = history.exclude(('quarter_period','quarter_period2'))
	history = history.rename(column_names=[
		'sponsor','current_wk_cost','current_wk_count','last_wk_cost','last_wk_count','week_raw','week_pct',
		'current_mth_cost','current_mth_count','last_mth_cost','last_mth_count','month_raw','month_pct',
		'current_qtr_cost','current_qtr_count','last_qtr_cost','last_qtr_count'])
	history = history.compute([
		('quarter_raw',agate.Formula(agate.Number(),lambda row: nullRawChange(row[15],row[13]))),
		('quarter_pct',agate.Formula(agate.Number(),lambda row: nullPctChange(row[15],row[13]))),
		])

	print 'Historical totals calculated...'

	history.to_csv(data_dest+'historical_totals.csv')
	s3.Object('mtduk.es', 'data/historical_totals.csv').put(Body=open(data_dest+'historical_totals.csv', 'rb'))

	print 'CSV saved to',data_dest+'historical_totals.csv','and S3'

def getBiggestChanges():
	print 'Calculating largest changes...'

	#pull in each table
	campaign_totals = agate.Table.from_csv(data_dest+'campaign_totals.csv')
	sponsor_totals = agate.Table.from_csv(data_dest+'sponsor_totals.csv')
	history = agate.Table.from_csv(data_dest+'historical_totals.csv')

	#sort each table by values
	sorted_by_week_raw = history.order_by('week_raw',reverse=True)
	sorted_by_week_raw = sorted_by_week_raw.select(('sponsor','week_raw'))
	top_week_raw = sorted_by_week_raw.limit(1).rename(('sponsor','amount'))
	top_week_raw = top_week_raw.compute([
		('detail',agate.Formula(agate.Text(),lambda row:'')),
		('change_type',agate.Formula(agate.Text(),lambda row:'largest change week over week'))
		])

	sorted_by_week_pct = history.where(lambda row: row['week_pct'] != None).order_by('week_pct',reverse=True)
	sorted_by_week_pct = sorted_by_week_pct.select(('sponsor','week_pct'))
	top_week_pct = sorted_by_week_pct.limit(1).rename(('sponsor','amount'))
	top_week_pct = top_week_pct.compute([
		('detail',agate.Formula(agate.Text(),lambda row:'')),
		('change_type',agate.Formula(agate.Text(),lambda row:'largest percentage change week over week'))
		])

	sorted_by_month_raw = history.order_by('month_raw',reverse=True)
	sorted_by_month_raw = sorted_by_month_raw.select(('sponsor','month_raw'))
	top_month_raw = sorted_by_month_raw.limit(1).rename(('sponsor','amount'))
	top_month_raw = top_month_raw.compute([
		('detail',agate.Formula(agate.Text(),lambda row:'')),
		('change_type',agate.Formula(agate.Text(),lambda row:'largest change month over month'))
		])

	sorted_by_month_pct = history.where(lambda row: row['month_pct'] != None).order_by('month_pct',reverse=True)
	sorted_by_month_pct = sorted_by_month_pct.select(('sponsor','month_pct'))
	top_month_pct = sorted_by_month_pct.limit(1).rename(('sponsor','amount'))
	top_month_pct = top_month_pct.compute([
		('detail',agate.Formula(agate.Text(),lambda row:'')),
		('change_type',agate.Formula(agate.Text(),lambda row:'largest percentage change month over month'))
		])

	sorted_by_quarter_raw = history.order_by('quarter_raw',reverse=True)
	sorted_by_quarter_raw = sorted_by_quarter_raw.select(('sponsor','quarter_raw'))
	top_quarter_raw = sorted_by_quarter_raw.limit(1).rename(('sponsor','amount'))
	top_quarter_raw = top_quarter_raw.compute([
		('detail',agate.Formula(agate.Text(),lambda row:'')),
		('change_type',agate.Formula(agate.Text(),lambda row:'largest change quarter over quarter'))
		])

	sorted_by_quarter_pct = history.where(lambda row: row['quarter_pct'] != None).order_by('quarter_pct',reverse=True)
	sorted_by_quarter_pct = sorted_by_quarter_pct.select(('sponsor','quarter_pct'))
	top_quarter_pct = sorted_by_quarter_pct.limit(1).rename(('sponsor','amount'))
	top_quarter_pct = top_quarter_pct.compute([
		('detail',agate.Formula(agate.Text(),lambda row:'')),
		('change_type',agate.Formula(agate.Text(),lambda row:'largest percentage change quarter over quarter'))
		])

	sorted_by_campaign = campaign_totals.order_by('total',reverse=True)
	sorted_by_campaign = sorted_by_campaign.select(('creative','total','sponsor'))
	top_campaign = sorted_by_campaign.limit(1).rename(('detail','amount','sponsor'))
	top_campaign = top_campaign.compute([
		('change_type',agate.Formula(agate.Text(),lambda row:'largest spend on a single ad to date'))
		])
	#reorder columns
	top_campaign = agate.Table([
		(top_campaign.rows[0]['sponsor'],top_campaign.rows[0]['amount'],
			top_campaign.rows[0]['detail'],top_campaign.rows[0]['change_type'])
		],['sponsor','amount','detail','change_type'
		])

	sorted_by_sponsor = sponsor_totals.order_by('sponsor_cost',reverse=True)

	top_sponsor = sorted_by_sponsor.limit(1).rename(('sponsor','amount'))
	top_sponsor = top_sponsor.compute([
		('detail',agate.Formula(agate.Text(),lambda row:'')),
		('change_type',agate.Formula(agate.Text(),lambda row:'biggest ad spender'))
		])

	#this doesn't work. logged error on github
	#biggest_changes = agate.Table.merge([top_week_pct,top_week_raw])

	biggest_changes = agate.Table([
		(top_week_raw.rows[0]),(top_month_raw.rows[0]),
		(top_quarter_raw.rows[0]),(top_campaign.rows[0]),(top_sponsor.rows[0])
		],['sponsor','amount','detail','change_type'
		])

	biggest_pct_changes = agate.Table([
		(top_week_pct.rows[0]),(top_month_pct.rows[0]),
		(top_quarter_pct.rows[0])
		],['sponsor','amount','detail','change_type'
		])

	print 'Largest changes calculated...'

	#write to file (these don't need to be saved to S3)
	biggest_changes.to_csv(data_dest+'biggest_changes.csv')
	print 'CSV saved to',data_dest+'biggest_changes.csv'

	biggest_pct_changes.to_csv(data_dest+'biggest_pct_changes.csv')
	print 'CSV saved to',data_dest+'biggest_pct_changes.csv'

def nullRawChange(value_before,value_after):
	if value_before != None:
		if value_after != None:
			return  value_after - value_before
		else:
			return 0 - value_before
	else:
		if value_after != None:
			return value_after
		else:
			return 0
		
def nullPctChange(value_before,value_after):
	if value_before != None:
		if value_after != None:
			return (value_after - value_before)/value_before
		else:
			return (0 - value_before)/value_before
	else:
		if value_after != None:
			return None
		else:
			return 0

def _getMondayDate(current_date):
    current_date -= datetime.timedelta(days=1)
    while current_date.weekday() > 0: # Mon-Fri are 0-4
        current_date -= datetime.timedelta(days=1)
    return current_date

def main():
	#s3 = boto3.resource('s3')
	filename = access_kantar()
	#add checks for existing calculations
	if filename != None:
		get_campaign_totals(data_dest + filename)
		get_sponsor_totals(data_dest + filename)
		get_historical_totals(data_dest + filename)
		getBiggestChanges()
	else:
		print 'No file to process'

if __name__ == '__main__':

	main()
	print 'Done. Have a nice day.'