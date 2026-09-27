#!/usr/bin/env python3
import sys, re
from decimal import Decimal, ROUND_HALF_UP, ROUND_HALF_EVEN, ROUND_FLOOR, ROUND_DOWN

D = Decimal
CENT = D('0.01')
TENTH = D('0.1')
TARIFFS = {
    'D': (10, 30, D('1.2050'), D('1.8575'), D('2.4410'), D('.3125')),
    'C': (50, 200, D('1.1500'), D('1.4025'), D('1.6550'), D('.9860')),
    'L': (10, 30, D('1.2050'), D('1.8575'), D('2.4410'), D('.3125')),
}

def q(v, unit=CENT, rounding=ROUND_HALF_UP):
    return D(v).quantize(unit, rounding=rounding)

def trunc(v, unit=CENT):
    return D(v).quantize(unit, rounding=ROUND_DOWN)

def comma(v, dec=2):
    return f'{abs(D(v)):,.{dec}f}'

def right_num(v, width, dec=2, blank_zero=False):
    if blank_zero and D(v) == 0:
        return ' ' * width
    return comma(v, dec)[-width:].rjust(width)

def currency(v, width, dec=2):
    n = comma(v, dec)
    s = '$' + n
    if len(s) > width:
        s = '$' + n[-(width-1):]
    return s.rjust(width)

def stars(v, width, dec=2):
    s = comma(v, dec)
    return s[-width:].rjust(width, '*')

def lead_sign(v, width, dec=2):
    sign = '-' if D(v) < 0 else '+'
    s = sign + comma(v, dec)
    return s[-width:].rjust(width)

def float_sign(v, width, dec=2):
    s = comma(v, dec)
    if D(v) < 0:
        s = '-' + s
    return s[-width:].rjust(width)

def trail_cr(v, width, dec=2):
    tail = 'CR' if D(v) < 0 else '  '
    s = comma(v, dec)
    return s[-(width-2):].rjust(width-2) + tail

def money_trailing(v, width):
    n = comma(v, 2)
    s = '$' + n
    body = width - 1
    if len(s) > body:
        s = '$' + n[-(body-1):]
    suffix = '-' if D(v) < 0 else ' '
    return s.rjust(body) + suffix

def signed_integer(v, width):
    s = str(abs(int(v)))
    if D(v) < 0:
        s = '-' + s
    return s[-width:].rjust(width)

def emit(out, s=''):
    out.write(s[:72].rstrip(' ').encode('ascii') + b'\n')

def records(path, width=80):
    with open(path, 'rb') as f:
        for raw in f:
            raw = raw.rstrip(b'\n')
            if raw.endswith(b'\r'):
                raw = raw[:-1]
            yield raw[:width].ljust(width, b' ').decode('ascii')

def digits(s):
    return int(s)

def parse_amount_text(s):
    # TEST-NUMVAL forms documented in the runbook. Return Decimal or None.
    if re.fullmatch(r' *[+-] *[0-9]*\.?[0-9]+ *| *[+-] *[0-9]+\.?[0-9]* *', s):
        t = s.strip()
        sign = 1
        if t[:1] in '+-':
            if t[0] == '-': sign = -1
            t = t[1:].strip()
        return D(t) * sign
    m = re.fullmatch(r' *([0-9]*\.?[0-9]+|[0-9]+\.?) *(\+|-|CR|DB)? *', s)
    if not m:
        return None
    v = D(m.group(1))
    if m.group(2) in ('-', 'CR'):
        v = -v
    return v

def unstring(line, old):
    vals = old[:]
    parts = line.split(';')
    fields = min(len(parts), 4)
    widths = (8, 3, 16, 30)
    acct_len = 0
    for i in range(fields):
        text = parts[i]
        moved = text[:widths[i]]
        vals[i] = moved.ljust(widths[i])
        if i == 0:
            acct_len = len(moved)
    return vals, fields, acct_len

def main(readings, payments, output):
    billed = rejected = credits = 0
    tot_units = 0
    tot_current = tot_due = tot_net = D(0)
    accounts = []
    with open(output, 'wb') as out:
        rs = iter(records(readings))
        first = next(rs, None)
        pending = [] if first is None else [first]
        if first is not None and first[0] == 'H':
            date, region = first[1:9], first[9:29]
            dmy = date[6:8] + date[4:6] + date[0:4]
            emit(out, 'STATEMENTS FOR ' + region + ' DATED ' + dmy[0:2]+'/'+dmy[2:4]+'/'+dmy[4:8])
            emit(out)
            pending = []
        for r in pending + list(rs):
            if r[0] != 'C':
                continue
            acct, name, tariff = r[1:9], r[9:33], r[33]
            prev, curr, days = digits(r[34:40]), digits(r[40:46]), digits(r[46:49])
            arrears = D(r[50:57]) / 100
            if r[49] == '-': arrears = -arrears
            paid = D(r[57:64]) / 100
            reason = ''
            if tariff not in TARIFFS: reason = 'UNKNOWN TARIFF'
            elif days == 0: reason = 'NO BILLING DAYS'
            elif days > 120: reason = 'PERIOD TOO LONG'
            if reason:
                rejected += 1
                emit(out, 'REJECT ' + acct + ' ' + reason.ljust(20))
                emit(out)
                continue
            lim1, lim2, rate1, rate2, rate3, standing_rate = TARIFFS[tariff]
            units = curr-prev if curr >= prev else curr+1000000-prev
            l1 = q(D(lim1*days)/30, TENTH)
            l2 = q(D(lim2*days)/30, TENTH)
            b1 = min(D(units), l1)
            b2 = D(0); b3 = D(0)
            if D(units) > l1:
                if D(units) > l2:
                    b2, b3 = l2-l1, D(units)-l2
                else: b2 = D(units)-l1
            c1, c2, c3 = q(b1*rate1), q(b2*rate2), q(b3*rate3)
            usage = c1+c2+c3
            standing = q(D(days)*standing_rate)
            discount = D(0)
            if tariff == 'L':
                discount = trunc(usage*D('.15'))
                usage -= discount
            net = usage+standing
            vat = q(net*D('.05'))
            current = net+vat
            interest = q(arrears*D('.015')) if arrears > 0 else D(0)
            balance = current+arrears+interest-paid
            due = balance if balance > 0 else D(0)
            carry = q(balance*D('.975')) if balance < 0 else D(0)
            if balance < 0: credits += 1
            billed += 1
            accounts.append([acct, balance])
            tot_units += units; tot_current += current; tot_due += due; tot_net += balance
            uname = name.upper()
            cut = uname.find('  ')
            if cut >= 0: uname = uname[:cut]
            if not uname: uname = '(NO NAME ON FILE)'
            uname = uname[:24].ljust(24)
            emit(out, 'ACCOUNT ****'+acct[4:8]+'  '+uname+' TARIFF '+tariff)
            emit(out, 'READINGS '+str(prev).rjust(6)+' TO '+str(curr).rjust(6)+'  USAGE '+f'{units:,}'.rjust(9)+' OVER '+str(days).rjust(3)+' DAYS')
            emit(out, 'BANDS '+right_num(b1,8,1)+' '+right_num(b2,8,1)+' '+right_num(b3,11,1))
            emit(out, 'USAGE CHARGE '+currency(usage,13)+'  STANDING'+currency(standing,10))
            emit(out, 'DISCOUNT '+right_num(discount,9,2,True)+'  VAT'+right_num(vat,10)+'  CURRENT'+currency(current,10))
            emit(out, 'ARREARS '+lead_sign(arrears,13)+'  INTEREST'+right_num(interest,9,2,True)+'  PAID'+right_num(paid,9))
            emit(out, 'BALANCE '+trail_cr(balance,14)+'  AMOUNT DUE'+stars(due,10))
            if balance < 0:
                emit(out, 'CREDIT C/F '+money_trailing(carry,11))
            emit(out)
        emit(out, 'ACCOUNTS BILLED '+str(billed).rjust(3)+'  REJECTED '+str(rejected).rjust(3)+'  CREDITS '+str(credits).rjust(3))
        emit(out, 'TOTAL UNITS '+f'{tot_units:,}'.rjust(11)+'  TOTAL CURRENT '+currency(tot_current,14))
        average = q(tot_current/D(billed)) if billed else D(0)
        emit(out, 'TOTAL DUE '+currency(tot_due,14)+'  AVERAGE BILL '+currency(average,13))
        emit(out, 'NET POSITION '+float_sign(tot_net,14))
        emit(out)
        emit(out, 'PAYMENTS AND ADJUSTMENTS')
        applied = payrej = line_no = 0
        tot_paid = tot_other = D(0)
        old = [' '*8, ' '*3, ' '*16, ' '*30]
        for line in records(payments):
            line_no += 1
            old, nf, alen = unstring(line, old)
            acct, kind, atxt, memo = old
            reason = ''
            val = parse_amount_text(atxt)
            if nf < 3: reason = 'TOO FEW FIELDS'
            elif alen != 8: reason = 'BAD ACCOUNT'
            elif val is None: reason = 'BAD AMOUNT'
            elif kind not in ('PAY','ADJ','FEE','REF'): reason = 'BAD KIND'
            idx = next((i for i,a in enumerate(accounts) if a[0] == acct), None) if not reason else None
            if not reason and idx is None: reason = 'NO SUCH ACCOUNT'
            if reason:
                payrej += 1
                emit(out, 'LINE '+str(line_no).rjust(3)+' REJECTED '+reason.ljust(20))
                continue
            if kind == 'PAY':
                amt = q(val, CENT, ROUND_HALF_EVEN); accounts[idx][1] -= amt; tot_paid += amt
            elif kind == 'ADJ':
                amt = q(val); accounts[idx][1] += amt; tot_other += amt
            elif kind == 'FEE':
                amt = trunc(val); accounts[idx][1] += amt; tot_other += amt
                part = q(amt/D(3)); rem = amt-part*3
            else:
                amt = q(val, CENT, ROUND_FLOOR); accounts[idx][1] += amt; tot_other += amt
            whole = int(D(amt).to_integral_value(rounding=ROUND_FLOOR))
            pos = memo.find('#')
            if pos >= 0:
                memo = memo[:pos+1] + ''.join('X' if c.isdigit() else c for c in memo[pos+1:])
            old[3] = memo
            applied += 1
            s = kind+' '+acct+' '+float_sign(amt,11)+' WHOLE '+signed_integer(whole,6)+' BAL '+trail_cr(accounts[idx][1],14)+' '+memo
            emit(out, s)
            if kind == 'FEE':
                emit(out, '    FEE SPLIT 3X'+float_sign(part,10)+' REMAINDER '+float_sign(rem,5))
        emit(out, 'POSTED  '+str(applied).rjust(3)+'  REJECTED '+str(payrej).rjust(3)+'  PAID  '+money_trailing(tot_paid,14)+'  OTHER '+money_trailing(tot_other,14))

if __name__ == '__main__':
    if len(sys.argv) != 4:
        raise SystemExit('usage: wbill.py <readings> <payments> <output>')
    main(*sys.argv[1:])
