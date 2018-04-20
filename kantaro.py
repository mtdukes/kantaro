import analyzeKantar
import generateTweet

# Import smtplib for the actual sending function
import smtplib
import datetime
import csv
import locale

secret_keys = []

def main():
	analyzeKantar.main()
	sendMail()

def sendMail():
	_get_secrets()

	#hacky fix to solve unpredictable locale problems
	try:
		locale.setlocale(locale.LC_ALL, 'en_US.utf8')
	except:
		locale.setlocale(locale.LC_ALL, 'en_US.UTF-8')

	session = smtplib.SMTP('smtp.gmail.com', 587)
	session.ehlo()
	session.starttls()
	session.login('kantaro.wral', secret_keys[3])
	headers = '\r\n'.join(['from: ' + 'kantaro.wral',
		'subject: ' + 'Kantaro report for ' + datetime.date.today().strftime('%m/%d/%Y'),
		#'to: ' + 'tdukes@wral.com',
		'to: ' + 'tdukes@wral.com'+',tfain@wral.com'+',lleslie@wral.com'+',dhendrickson@wral.com'+',mburns@wral.com',
		'mime-version: 1.0',
		'content-type: text/html'])

	ad_variables = []
	with open('data/biggest_changes.csv','rU') as csv_input:
		reader = csv.reader(csv_input)
		reader.next()
		for row in reader:
			ad_variables.append(
				[row[0].title(),
				locale.format('%d',int(row[1]),grouping=True),
				row[2].title()]
				)

	with open('data/biggest_pct_changes.csv','rU') as csv_input:
		reader = csv.reader(csv_input)
		reader.next()
		for row in reader:
			ad_variables.append(
				[row[0].title(),
				round((float(row[1])*100),1),
				row[2].title()]
				)

	with open('text/email_body.txt','r') as f:
		email_body = f.read()

	# body_of_email can be plaintext or html!
	content = headers + "\r\n\r\n" + email_body.format(
		ad_variables[5][0],ad_variables[5][1],
		ad_variables[0][0],ad_variables[0][1],
		ad_variables[1][0],ad_variables[1][1],
		#ad_variables[6][0],ad_variables[6][1],
		ad_variables[2][0],ad_variables[2][1],
		#ad_variables[7][0],ad_variables[7][1],
		ad_variables[3][0],ad_variables[3][1],ad_variables[3][2],
		ad_variables[4][0],ad_variables[4][1],
		)
	session.sendmail('kantaro.wral', ['tdukes@wral.com','tfain@wral.com','lleslie@wral.com','dhendrickson@wral.com','mburns@wral.com'], content)
	#session.sendmail('kantaro.wral', ['tdukes@wral.com'], content)

	print 'Email sent...'

def _get_secrets():
	global secret_keys
	with open('.keys') as f:
		secret_keys = f.read().splitlines()

if __name__ == '__main__':
	main()