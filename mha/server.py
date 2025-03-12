from flask import Flask, render_template, request, current_app
from email.parser import HeaderParser
import time
import dateutil.parser
from datetime import datetime
import re
import pygal
from pygal.style import Style
from IPy import IP
import geoip2.database
import os
import argparse
import logging

def create_app(test_config=None):
    """Application factory function"""
    app = Flask(__name__)
    
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Load GeoIP database
    geoip_path = os.path.join(app.static_folder, 'data/GeoLite2-Country.mmdb')
    if not os.path.exists(geoip_path):
        app.logger.warning(f"GeoIP database not found at {geoip_path}. Geolocation features will be disabled.")
        reader = None
    else:
        try:
            reader = geoip2.database.Reader(geoip_path)
            app.logger.info("GeoIP database loaded successfully")
        except Exception as e:
            app.logger.error(f"Failed to load GeoIP database: {e}")
            reader = None
    
    app.config['GEOIP_READER'] = reader
    
    @app.context_processor
    def utility_processor():
        def getCountryForIP(line):
            if not current_app.config['GEOIP_READER']:
                return None
                
            ipv4_address = re.compile(r"""
                \b((?:25[0-5]|2[0-4]\d|1\d\d|[1-9]\d|\d)\.
                (?:25[0-5]|2[0-4]\d|1\d\d|[1-9]\d|\d)\.
                (?:25[0-5]|2[0-4]\d|1\d\d|[1-9]\d|\d)\.
                (?:25[0-5]|2[0-4]\d|1\d\d|[1-9]\d|\d))\b""", re.X)
            ip = ipv4_address.findall(line)
            if ip:
                ip = ip[0]  # take the 1st ip and ignore the rest
                try:
                    if IP(ip).iptype() == 'PUBLIC':
                        r = current_app.config['GEOIP_READER'].country(ip).country
                        if r.iso_code and r.name:
                            return {
                                'iso_code': r.iso_code.lower(),
                                'country_name': r.name
                            }
                except Exception as e:
                    current_app.logger.warning(f"Error looking up IP {ip}: {str(e)}")
                    return None
            return None
        return dict(country=getCountryForIP)

    @app.context_processor
    def duration_processor():
        def duration(seconds, _maxweeks=99999999999):
            return ', '.join(
                f"{num} {unit}"
                for num, unit in zip([
                    (seconds // d) % m
                    for d, m in (
                        (604800, _maxweeks),
                        (86400, 7), (3600, 24),
                        (60, 60), (1, 60))
                ], ['wk', 'd', 'hr', 'min', 'sec'])
                if num
            )
        return dict(duration=duration)

    def dateParser(line):
        try:
            return dateutil.parser.parse(line, fuzzy=True)
        except ValueError:
            # if the fuzzy parser failed to parse the line due to
            # incorrect timezone information issue #5 GitHub
            try:
                r = re.findall(r'^(.*?)\s*(?:\(|utc)', line, re.I)
                if r:
                    return dateutil.parser.parse(r[0])
                return datetime.now()  # fallback
            except Exception as e:
                current_app.logger.error(f"Date parsing error: {str(e)}")
                return datetime.now()  # fallback

    def getHeaderVal(h, data, rex=r'\s*(.*?)\n\S+:\s'):
        r = re.findall(f'{h}:{rex}', data, re.X | re.DOTALL | re.I)
        return r[0].strip() if r else None

    @app.route('/', methods=['GET', 'POST'])
    def index():
        if request.method == 'POST':
            try:
                mail_data = request.form['headers'].strip()
                r = {}
                n = HeaderParser().parsestr(mail_data)
                graph = []
                
                # Extract and process received headers
                received = n.get_all('Received')
                if received:
                    received = [i for i in received if ('from' in i or 'by' in i)]
                else:
                    received = re.findall(
                        r'Received:\s*(.*?)\n\S+:\s+', mail_data, re.X | re.DOTALL | re.I)
                
                c = len(received)
                for i in range(len(received)):
                    try:
                        if ';' in received[i]:
                            line = received[i].split(';')
                        else:
                            line = received[i].split('\r\n')
                        line = list(map(str.strip, line))
                        line = [x.replace('\r\n', ' ') for x in line]
                        
                        try:
                            if i + 1 < len(received):
                                if ';' in received[i + 1]:
                                    next_line = received[i + 1].split(';')
                                else:
                                    next_line = received[i + 1].split('\r\n')
                                next_line = list(map(str.strip, next_line))
                                next_line = [x.replace('\r\n', '') for x in next_line]
                            else:
                                next_line = None
                        except IndexError:
                            next_line = None

                        org_time = dateParser(line[-1])
                        next_time = org_time if not next_line else dateParser(next_line[-1])

                        # Extract direction information
                        if line[0].startswith('from'):
                            data = re.findall(
                                r"""
                                from\s+
                                (.*?)\s+
                                by(.*?)
                                (?:
                                    (?:with|via)
                                    (.*?)
                                    (?:\sid\s|$)
                                    |\sid\s|$
                                )""", line[0], re.DOTALL | re.X)
                        else:
                            data = re.findall(
                                r"""
                                ()by
                                (.*?)
                                (?:
                                    (?:with|via)
                                    (.*?)
                                    (?:\sid\s|$)
                                    |\sid\s
                                )""", line[0], re.DOTALL | re.X)

                        # Calculate delay
                        delay = (org_time - next_time).total_seconds()
                        delay = max(0, delay)  # Ensure non-negative delay

                        try:
                            ftime = time.strftime('%m/%d/%Y %I:%M:%S %p', org_time.utctimetuple())
                            r[c] = {
                                'Timestmp': org_time,
                                'Time': ftime,
                                'Delay': delay,
                                'Direction': [x.replace('\n', ' ') for x in list(map(str.strip, data[0]))]
                            }
                            c -= 1
                        except (IndexError, AttributeError) as e:
                            current_app.logger.warning(f"Error processing hop {i}: {str(e)}")
                    except Exception as e:
                        current_app.logger.error(f"Error processing received header {i}: {str(e)}")
                        continue

                # Create graph data
                for i in r.values():
                    try:
                        if i['Direction'][0]:
                            graph.append(["From: %s" % i['Direction'][0], i['Delay']])
                        else:
                            graph.append(["By: %s" % i['Direction'][1], i['Delay']])
                    except (IndexError, KeyError) as e:
                        current_app.logger.warning(f"Error creating graph data: {str(e)}")

                # Calculate total delay
                totalDelay = sum(x['Delay'] for x in r.values())
                fTotalDelay = duration_processor()['duration'](int(totalDelay))
                delayed = True if totalDelay else False

                # Create visualization
                custom_style = Style(
                    background='transparent',
                    plot_background='transparent',
                    font_family='googlefont:Open Sans',
                )
                line_chart = pygal.HorizontalBar(
                    style=custom_style, 
                    height=250, 
                    legend_at_bottom=True,
                    tooltip_border_radius=10
                )
                line_chart.tooltip_fancy_mode = False
                line_chart.title = f'Total Delay is: {fTotalDelay}'
                line_chart.x_title = 'Delay in seconds'
                
                for i in graph:
                    line_chart.add(i[0], i[1])
                chart = line_chart.render(is_unicode=True)

                # Prepare email summary
                summary = {
                    'From': n.get('From') or getHeaderVal('from', mail_data),
                    'To': n.get('to') or getHeaderVal('to', mail_data),
                    'Cc': n.get('cc') or getHeaderVal('cc', mail_data),
                    'Subject': n.get('Subject') or getHeaderVal('Subject', mail_data),
                    'MessageID': n.get('Message-ID') or getHeaderVal('Message-ID', mail_data),
                    'Date': n.get('Date') or getHeaderVal('Date', mail_data),
                }

                # Enhanced security headers list
                security_headers = [
                    'Received-SPF', 
                    'Authentication-Results',
                    'DKIM-Signature', 
                    'ARC-Authentication-Results',
                    'DMARC', 
                    'ARC-Seal',
                    'ARC-Message-Signature'
                ]
                
                return render_template(
                    'index.html', 
                    data=r, 
                    delayed=delayed, 
                    summary=summary,
                    n=n, 
                    chart=chart, 
                    security_headers=security_headers
                )
            except Exception as e:
                current_app.logger.error(f"Error processing request: {str(e)}")
                return render_template('index.html', error=f"Error processing email headers: {str(e)}")
        else:
            return render_template('index.html')

    return app

def run_app():
    """Run the application from command line"""
    parser = argparse.ArgumentParser(description="Mail Header Analyzer")
    parser.add_argument("-d", "--debug", action="store_true", default=False,
                        help="Enable debug mode")
    parser.add_argument("-b", "--bind", default="127.0.0.1", type=str,
                        help="IP address to bind to")
    parser.add_argument("-p", "--port", default="8080", type=int,
                        help="Port to listen on")
    args = parser.parse_args()

    app = create_app()
    app.debug = args.debug
    app.run(host=args.bind, port=args.port)

if __name__ == '__main__':
    run_app()
