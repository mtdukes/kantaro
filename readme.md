# Kantaro

Kantaro is an automated system for retrieving political ad spending data, peforming basic analysis and doing some stupid robot tricks with it. Uses proprietary data from Kantar media.

A work in progress, with documentation here on Github mostly so we don't forget.

## Requirements
Kantaro uses a number of python libraries, most notably [agate](https://source.opennews.org/en-US/articles/introducing-agate/). It's pretty sweet.

Other requirements are accessible via requirements.txt.

```
pip install -r requirements.txt
```

The generateTweet.py script also requires the use of [ffmpeg](https://www.ffmpeg.org/) to process video. A few ways to do it. [One way here](http://stackoverflow.com/questions/29125229/how-to-reinstall-ffmpeg-clean-on-ubuntu-14-04).

## analyzeKantar.py

Primary script for accessing and parsing data using agate. Takes no arguments.

Usage:

```
python analyzeKantar.py
```

On execution:

- Downloads latest Kantar data
- Generates a series of separate CSVs in /data/
 - **campaign_totals.csv** The total ad spend for each distinct ad campaign/commercial
 - **sponsor_totals.csv** The total ad spend for each ad sponsor
 - **historical_totals.csv** The raw and percent change in spending week over week, month over month, three-month period over three-month period (quarter) on a rolling basis
 - **biggest_changes.csv** The most expensive campaign and biggest spending sponsor, as well as the largest raw change in spending week over week, month over month and quarter over quarter
 - **biggest_pct_changes.csv** the largest percentage change in spending week over week, month over month and quater over quarter

All rolling date calculations are based on weeks (1,4 and 13) that run from Tuesday to Monday, since Kantar data is released every Tuesday.

## generateTweet.py

Mostly an experiment to see if we can use Kantar data and Wordsmith from Automated Insights to generate narrative and tweets. Queries the Wordsmith API for text content using a random line of data from data/campaign_totals.csv, downloading the ad video and converting it into an abbreviated GIF file stored in /img/.

Usage:

```
python generateTweet.py
```

## kantaro.py

Main script to tie everything together. Emails report upon successful completion of task. Email body text constructed from /text/email_body.txt.

Usage:

```
python kantaro.py
```

## TODO

- [ ] Install [mail service](http://askubuntu.com/questions/222512/cron-info-no-mta-installed-discarding-output-error-in-the-syslog) to alert for errors
- [ ] Add error checking for continuously checking for new Kantar file around release time
- [ ] Use emails as external variables in kantaro.py
- [ ] Additional tweet functionality
- [ ] Create alternative to Wordsmith API
- [ ] Add "new on the scene" report to email and spreadsheet
- [ ] Integrate boto/s3 so we can store and access CSVs
- [ ] Add link generation to kantaro email to access CSVs
- [ ] Fix N/As and blanks in some tweets from source data
- [ ] Add check to see if something has already been tweeted.
- [ ] Refactor. (\/) (°,,,°) (\/) Your code is bad and you should feel bad.

## Running a cron job

Manual kantaro scripts can be run in the command line. You can also run the master kantaro.py script in crontab, accessible via nano at /etc/crontab. Crontab parameters describe the timing when your command should run, separated by spaces:

1. m - minute (0-59)
2. h - hour (0-23, server time typically UTC, so add 5)
3. dom - day of month (1-31)
4. mon - month (1-12)
5. dow - day of week (0-6, Sunday is 0)

So if you wanted to run a script at 3 p.m. every Monday, you add:

```
0 20 * * 1 your_username python script.py
```

## Fine print stuff

Created by [Tyler Dukes](https://github.com/mtdukes), reporter for [WRAL News](https://github.com/wraldata)