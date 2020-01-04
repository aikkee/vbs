import os
import json
import datetime
import flask_excel as excel
import flask_sqlalchemy 

from flask import Flask, render_template, redirect, session, url_for, \
                  request, make_response, send_from_directory, abort, flash
from sqlalchemy import and_
from datetime import date, timedelta
from flask_wtf import FlaskForm
from wtforms import StringField, SelectField, HiddenField, validators
from flask_sqlalchemy import SQLAlchemy

application = Flask(__name__)
application.config.from_pyfile('bookings.cfg')
db = SQLAlchemy(application)
excel.init_excel(application)


# -- Forms --
class BookingForm(FlaskForm):
    location = SelectField('location')
    date_time = SelectField('date_time')
    rtype = HiddenField('rtype')
    booking_ref = HiddenField('booking_ref')
    expire_on = HiddenField('expire_on')

# -- Models --
class Resource(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    rtype = db.Column(db.String(10)) # Resource Type
    location = db.Column(db.String(10))
    description = db.Column(db.String(20))
    capacity = db.Column(db.Integer)
    available = db.Column(db.Integer)

    def __repr__(self):
        return '<Resource %r, %r, %r, %r, %r>' % (self.rtype, self.location, self.description, \
            self.capacity, self.available)

class Reference(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    resource_type = db.Column(db.String(10), unique=True) # Resources that this reference can book
    booking_ref = db.Column(db.String(10), unique=True) # reference made to the person who make a booking
    expire_on = db.Column(db.DateTime)
    resource_id = db.Column(db.Integer, db.ForeignKey('resource.id'))
    update_on = db.Column(db.DateTime)

    def __repr__(self):
        return '<Reference %r, %r>' % (self.booking_ref, self.expire_on)


# -- Views --
@application.route('/')
@application.route('/index')
def index():
    return render_template('index.html')

@application.route('/init')
def init():
    ref = request.args.get('ref')
    isnew = request.args.get('isnew')
    rtype = request.args.get('rtype')
    # also use this as the indicator for where the request comes from
    if (isnew is None or isnew==''):
        isnew='yes'

    if (isValidReference(ref, rtype) == False):
        return redirect(url_for('index'))

    if (ref is None or ref == ''):
        return redirect(url_for('index'))

    # TODO: Improve the query later by combining the 2 statements
    reference = Reference.query.filter(Reference.booking_ref==ref).first()
    booked_resource = Resource.query.filter(Resource.id==reference.resource_id).first()
    # Need to also handle cases where user use the same link to amend booking
    # When initiated from user through the sms link, isnew will be 'yes'
    # When initiated from change_booking page, isnew will be 'no'
    if (isnew=='yes' and booked_resource!=None):
        m = {'location':booked_resource.location, \
              'date_time':booked_resource.description}
        b = [{'ref':ref, 'rtype':rtype, 'isnew':'no', 'label':'Yes'}]
        return render_template('change_booking.html', message=m, buttons=b)

    # obtain the resource slots from database
    # available_resource = Resource.query.filter(Resource.available>0)
    bookingForm = BookingForm()
    # bookingForm.date_time.choices = [('', 'Choose Date & Time')] + [ (t.id, t.description) for t in available_resource]
    bookingForm.date_time.choices = [('', 'Choose Date & Time')]

    # obtain locations of available slots
    resources = Resource.query.filter(and_(Resource.available>0, Resource.rtype==rtype)).all()

    locations = list(set([(r.location) for r in resources if show_for_booking(r, str(reference.expire_on), rtype)]))
    bookingForm.location.choices = [('', 'Choose Location')] + [
        (l, l) for l in locations]
    
    bookingForm.booking_ref.data = ref
    bookingForm.rtype.data = rtype
    if (reference != None):
        bookingForm.expire_on.data = reference.expire_on
    return render_template('book_htmb_form.html', form=bookingForm, isnew='yes')

@application.route('/save', methods=['POST'])
def save():

    if (request.form.get('date_time')==""):
        flash('Both fields are required.')
        return redirect(redirect_url())

    b_ref = request.form.get('booking_ref')
    r_id = request.form.get('date_time', type=int)

    reference = Reference.query.filter(Reference.booking_ref==b_ref).first()
    # Release booking slot
    if (reference is not None and reference.resource_id is not None):
        booked_resource = Resource.query.filter(Resource.id==reference.resource_id).first()
        if (booked_resource is not None):
            booked_resource.available = booked_resource.available + 1 
            application.logger.info('Return slot for Resource ID: %r' % booked_resource.id)
            db.session.commit()

    resource = Resource.query.filter(Resource.id==r_id).first()
    if (resource.available == 0):
        # Fully booked, cannot accept anymore
        m = {'location':resource.location, \
             'date_time':resource.description}
        b = [{'ref':b_ref, 'label':'OK'}]
        return render_template('fully_booked.html', message=m, buttons=b)
    else:
        # update new booking
        reference.resource_id = r_id
        reference.update_on = datetime.datetime.now()
            
        resource.available = resource.available - 1 

        application.logger.info('Draw down from Resource ID: %s for Reference ID: %s' % (r_id, reference.id))

        db.session.commit()
        flash('Thank you for your submission.  Your session on %s at %s is confirmed.' %
              (resource.description, resource.location))

        l = {'url': get_gcal_url(resource.location, resource.description)}
        return render_template('acknowledge.html', gcal_link=l)

def get_gcal_url(location, dt_str):
    addrLookup = {
        "Alexandra Road":"460%20Alexandra%20Road%20%2302-15%20PSA%20Building%20S%28119963%29",
        "Boon Lay":"1%20Jurong%20West%20Central%202%20Jurong%20Point%20Shopping%20Centre%20%2301-17E%2FF%2FG/H%20S%28648886%29",
        "Buangkok":"10%20Sengkang%20Central%20%2301-04%20Buangkok%20MRT%20S%28545061%29",
        "Bukit Panjang":"1%20Jelebu%20Road%20%2303-02%20Bukit%20Panjang%20Plaza%20S%28677743%29",
        "Changi Business Park":"2%20Changi%20Business%20Park%20Ave%201%20%2301-03%20UE%20Biz%20Hub%20East%20S%28486015%29",
        "Clementi":"Blk%20451%20Clementi%20Avenue%203%20%2301-309%20S%28120451%29",
        "Esplanade":"90%20Bras%20Brasah%20Rd%20%23B1-02%20Esplanade%20MRT%20Station%20S%28189562%29",
        "Harbourfront":"1%20Harbourfront%20Place%20%2301-04%20Harbourfront%20Tower%201%20S%28098633%29",
        "Kovan":"205%20Hougang%20St%2021%20%2303-20%20Heartland%20Mall%20S%28530205%29",
        "Marina Bay":"8A%20Marina%20Boulevard%20%23B2-76%20Marina%20Bay%20Link%20Mall%20S%28018984%29",
        "Orchard":"333%20Orchard%20Road%20%2306-01%20Mandarin%20Orchard%20S%28238867%29",
        "Pasir Ris":"Blk%20625%20Elias%20Road%20%2301-324B%20S%28510625%29",
        "Paya Lebar":"10%20Eunos%20Road%208%20%2302-122%20Singapore%20Post%20Centre%20S%28408600%29",
        "Punggol":"Blk%20681%20Punggol%20Dr%20%2301-01%20S%28820681%29",
        "Raffles Place (ORQ)":"1%20Raffles%20Quay%20North%20Tower%20%2309-02%20S%28048583%29",
        "Raffles Place (ACB)":"11%20Collyer%20Quay%20%2319-01%20The%20Arcade%20S%28049317%29",
        "Raffles Place (PAC)":"11%20Collyer%20Quay%20%2318-01%20The%20Arcade%20S%28049317%29",
        "Serangoon":"Blk%20263%20Serangoon%20Central%20Dr%20%2301-59%20S%28550263%29",
        "Shenton Way":"50%20Robinson%20Road%20%2301-03%20Robinson%20Suites%20S%28068882%29",
        "Tanjong Pagar":"10%20Anson%20Road%20%2336-01%20International%20Plaza%20S%28079903%29",
        "Toa Payoh":"Blk%20126%Lorong%201%20Toa%20Payoh%20%2301-561%20S%28310126%29",
        "Woodlands":"30%20Woodlands%20Ave%202%20%2301-47%2F48%2F49%20Woodlands%20MRT%20Station%20S%28738343%29",
        "Sentosa (RWS)":"26%20Sentosa%20Gateway%20%23B2-01%20Resort%20World%20At%20Sentosa%20S%28098138%29",
        "Yishun Ring":"Blk%20598%20Yishun%20Ring%20Road%20Wisteria%20Mall%20%23B1-09%20S%28768698%29",
        "SCDF HQ Med Center":"91%20Ubi%20Ave%204%20S%28408827%29",
        "CDA Med Center":"101%20Jalan%20Bahar%20S%28649734%29"}

    try:
        start_dt = datetime.datetime.strptime(dt_str, '%d %b %Y - %I.%M%p')
    except ValueError:
        start_dt = datetime.datetime.strptime(dt_str, '%d %b %Y - %I%p')
    end_dt = start_dt + timedelta(hours=2)
    start_dt_str = start_dt.strftime("%Y%m%dT%H%M00")
    end_dt_str = end_dt.strftime("%Y%m%dT%H%M00")
    t = "http://www.google.com/calendar/event?action=TEMPLATE&" \
        "dates="+ start_dt_str +"/" + end_dt_str + "&ctz=Asia/Singapore&" \
        "text=Pre-IPPT%20Medical%20Screening&location=" + addrLookup[location] + "&" \
        "details=You%20need%20to%20fast%20for%20eight%20hours%20before%20your%20appointment%20at%20Parkway%20Shenton%20clinic." \
        "%20%20Otherwise%20you%20will%20not%20be%20allowed%20to%20be%20screened.%0A%0APlease%20bring%20your%20FY20%20notification" \
        "%20letter%20/%20medical%20screening%20form%20and%20your%20NRIC%20to%20the%20clinic%20on%20the%20day%20of%20your" \
        "%20appointment%20for%20identification%20purpose.%20%0A%0APlease%20bring%20along%20your%20existing%20HTMB%20slips" \
        "%20and/or%20any%20other%20specialist%20memos.%20The%20doctors%20at%20Parkway%20Shenton%20need%20the%20HTMB%20results" \
        "%20/%20specialist%20memos%20to%20provide%20an%20accurate%20certification."
    return t 

def redirect_url(default='index'):
    return request.args.get('next') or \
           request.referrer or \
           url_for(default)

# Function to filter out and handle expiry date
# rtype determines the type of resources to be retreived, hence it should not be None
def show_for_booking(resource, exp, rtype, location=None):
    # handle reference expiry date

    exp_date = date( int(exp[:4]), int(exp[5:7]), int(exp[8:10]) )
    earliest_date = exp_date + datetime.timedelta(days=3)
    # change resource description to date object
    resource_date = datetime.datetime.strptime(resource.description[:11], '%d %b %Y').date()
    if (location == None):
        return resource.available > 0 and resource.rtype == rtype and resource_date > earliest_date
    else:
        return resource.location == location and resource.rtype == rtype and resource.available > 0 and resource_date > earliest_date
         

#TODO
@application.route("/slotsfor/<location>/", methods=["GET", "POST"])
def get_slots(location):
    resources = Resource.query.all()
    ref_expiry = request.args['expire_on']
    rtype = request.args['rtype']
    data = [
        (r.id, r.description) for r in resources if show_for_booking(r, ref_expiry, rtype, location) 
    ]
    response = make_response(json.dumps(data))
    response.content_type = 'application/json'
    return response


def isValidReference(booking_ref, rtype):
    bRef = Reference.query.filter(and_(Reference.booking_ref==booking_ref,
                                       Reference.resource_type==rtype,
                                       Reference.expire_on>datetime.datetime.now())).first()
    if (bRef != None):
        return True
    else:
        flash('Invalid reference <%s>. Please contact HRSS.' % booking_ref)
        return False

@application.route('/admin/check_slots')
def check_slots():
    return render_template('show_slots.html', slots=Resource.query.all())

@application.route("/admin/add_case", methods=['GET', 'POST'])
def add_case():
    # handle submission
    if request.method == 'POST':
        rtype = request.form.get('rtype')
        ref = request.form.get('ref')
        expiry = request.form.get('expiry')
        r = create_new_reference(rtype, ref, expiry)
        flash('%s activated. Expires on %s.' \
                % (r.booking_ref, r.expire_on.strftime('%d-%b-%Y')))
        return render_template('add_case.html')

    return render_template('add_case.html')

def create_new_reference(rtype, ref, expiry):
    r = Reference()
    r.resource_type = rtype
    r.booking_ref = ref 
    expiry_str = expiry + " 16:00:00" #handle timezone of server - 8 hrs behind us
    r.expire_on = datetime.datetime.strptime(expiry_str, "%Y-%m-%d %H:%M:%S")
    db.session.add(r)
    db.session.commit()
    return r

@application.route("/admin/import_case", methods=['GET', 'POST'])
def import_case():
    if (request.method == 'POST'):
        def ref_init_func(row):
            r = Reference()
            r.resource_type = row['RESOURCE_TYPE']
            r.booking_ref = row['BOOKING_REF']
            r.expire_on = datetime.datetime.strptime(str(row['EXPIRE_ON']), "%Y-%m-%d %H:%M:%S")
            return r
        request.save_to_database(field_name='file', session=db.session, \
                                      table=Reference, \
                                      initializer=(ref_init_func))
        flash('IPPT Medical Screening cases created.')
        return render_template('admin_acknowledge.html')
    return render_template('import.html', title='Import IPPT Medical Screening Cases')

@application.route("/admin/import_slot", methods=['GET', 'POST'])
def import_slot():
    if (request.method == 'POST'):
        def resource_init_func(row):
            r = Resource()
            r.rtype = row['TYPE']
            r.location = row['LOCATION']
            r.description = row['DESCRIPTION']
            r.capacity = row['CAPACITY']
            r.available = row['CAPACITY']
            return r
        request.save_to_database(field_name='file', session=db.session, \
                                      table=Resource, \
                                      initializer=(resource_init_func))
        flash('IPPT Medical Screening timeslot created.')
        return render_template('admin_acknowledge.html')
    return render_template('import.html', title='Import IPPT Medical Screening Timeslot')

@application.route("/admin/export_booking", methods=['GET'])
def doexport():

    col = ['resource_type', 'booking_ref','description', 'update_on', 'location']
    qs = Reference.query.join(Resource, Reference.resource_id == Resource.id).add_columns( \
            Reference.resource_type, Reference.booking_ref, Resource.description, \
            Reference.update_on, Resource.location).filter( \
                Reference.resource_id != None)
    return excel.make_response_from_query_sets(qs, col, "csv")

@application.errorhandler(404)
def page_not_found(e):
    return render_template('404.html'), 404

#----------test codes----------------------
@application.route('/<path:resource>')
def serveStaticResource(resource):
    return send_from_directory('static/', resource)

@application.route("/test")
def test():
    user_agent = request.headers.get('User-Agent')
    return "<p>It's Alive!<br/>Your browser is %s</p>" % user_agent

#----------main codes----------------------
if __name__ == '__main__':
    application.run(host='0.0.0.0', port=8080)
