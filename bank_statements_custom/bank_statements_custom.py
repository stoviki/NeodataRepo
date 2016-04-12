#-*- coding: utf-8 -*-
from openerp.osv import osv, fields
from openerp import models, api
import base64
import logging

_logger = logging.getLogger(__name__)

class bank_statements_custom(models.Model):
    _name = 'bank.statements.custom'
    
    _columns = {                 
                "account_id": fields.many2one('account.account', 'Account', select=1),
                "account_num": fields.char('Account'),
                "statement_date": fields.char ('Statement date'),
                "number": fields.integer('Number'),
                "total_income": fields.float('Total Income'),
                "total_outcome": fields.float('Total Outcome'),
                "initial_balance": fields.float('Initial Balance'),  # pocetno saldo                
                "name": fields.char('Name', required=True),
                "bank_id": fields.many2one('res.bank', 'Bank', select=1, required=True),
                "company_id": fields.many2one('res.company', 'Company'),
                "partner_id": fields.many2one('res.partner'),
                "content": fields.char('Content', readonly=True),
                "imported_file": fields.binary('Statement', required=True),
                "file_name": fields.char('Filename'),
                "import_date" : fields.date ('Import date'),
                "statement_line" : fields.one2many('bank.statement.line', 'statement_id', 'Statement Line'), 
                "hide_button": fields.boolean()
    } 
    
    #treba za jazikot na pdf reportot   
    @api.model
    def get_company_as_partner(self):
        companyID=self.env['res.company']._company_default_get('res.partner')
        Partner = self.env['res.partner']
        partner = Partner.browse(companyID)    
        return partner.id 
    
    def get_default_company(self, cr, uid, context=None):
        company_id = self.pool.get('res.users')._get_company(cr, uid, context=context)
        if not company_id:
            raise osv.except_osv(_('Error!'), _('There is no default company for the current user!'))
        return company_id
    
    _defaults = { 
                "company_id": get_default_company, 
                "partner_id": get_company_as_partner,
                "hide_button": False,
    }  
    
    @api.one
    def get_customer_voucher(self, c_voucher):        
        if c_voucher is None:
            return None
        else:
            return c_voucher.id
    @api.one
    def get_supplier_voucher(self, s_voucher):
        if s_voucher is None:
            return None
        else:
            return s_voucher.id
    
    @api.onchange('file_name')
    def set_statement_name(self):  
        self.name = self.file_name
            
    # metod za importiranje na izvod
    @api.one
    def import_statement(self):
        name = self.file_name
        bank = self.bank_id.bic                          
        invoices = self.env['account.invoice']
        voucher_customer = None
        voucher_supplier = None
        if isinstance(bank, basestring) and name.endswith(bank):
            
            # Stopanska Banka (kodot na bankata ke bide ekstenzija na fajlot so izvodot)
            if bank=='txt':    
                content = base64.decodestring(self.imported_file) 
                statement_lines = content.split('\n') #niza od stavki vo izvodot
                lines_num = len(statement_lines) #broj na stavki vo izvod
                
                #vcituvanje na informaciite za izvodot
                statement_info = statement_lines[0]                
                self.account_num = statement_info[1:16]                
                self.statement_date = statement_info[16:26]                
                self.number = statement_info[26:29]                
                self.total_income = statement_info[35:49]                
                self.total_outcome = statement_info[49:63]                
                self.initial_balance = statement_info[63:81]               
                
                line_num = 1 #content_lines[0] e vodeckiot slog na izvodot 
                              
                #kreiranje nova stavka vo baza
                while (line_num < lines_num):
                    
                    statement_line = statement_lines[line_num].decode('utf-8') #poedinecna stavka                  
                              
                    #Spored specifikaciite od Stopanska Banka:
                    line_income = statement_line[5:19] #priliv
                    line_outcome = statement_line[19:33] #odliv
                    line_account_num = statement_line[33:48] #smetka             
                    line_customer_name = statement_line[48:118] #naziv na nalogodavac/nalogoprimac  
                    line_customer_address = statement_line[118:143] #sediste na nalogodavac/nalogoprimac 
                    line_tax_num = statement_line[143:156] #danocen broj                   
                    line_payment_id = statement_line[156:159] #sifra na plakjanje                
                    line_povik_br_dolzi = statement_line[159:183] #povik na broj dolzi
                    line_povik_br_pobaruva = statement_line[183:207] #povik na broj pobaruva    
                    line_doznaka = statement_line[207:277] #cel na doznaka
                    line_date = statement_line[277:287] #datum
                    line_br_reklamacija = statement_line[287:317] #broj na reklamacija   
                    
                    s_line = self.statement_line.create({
                        "statement_id": self.id,                                                                                                                                         
                    })
                    
                                           
                    #azuriranje na balansot na izleznite fakturi (priliv na sredstva)
                    if line_povik_br_dolzi != '' and line_income != '00000000000.00':
                        invoice_num = line_povik_br_dolzi.rstrip()                        
                        outgoing_invoice = invoices.search([('number','=', invoice_num), ('type', '=', 'out_invoice')])  
                        invoice = outgoing_invoice
                        if invoice.state == 'open':
                            if invoice and invoice.residual > 0:
                                invoice.residual = invoice.residual - float(line_income)
                                tmp = invoice.residual 
                                payable_amount = float(line_income) # The amount you want to pay
                                    
                                voucher_customer = self.env['account.voucher'].create({
                                        "name": "",
                                        "amount": payable_amount,
                                        "journal_id": self.env['account.journal'].search([('type', '=', 'bank')], limit=1).id,
                                        "account_id": invoice.partner_id.property_account_receivable.id,
                                        "period_id": self.env['account.voucher']._get_period(),
                                        "partner_id": invoice.partner_id.id,
                                        "type": "receipt"
                                })
                                    
                                voucher_line_customer = self.env['account.voucher.line'].create({
                                        "name": "",                                        
                                        "amount": payable_amount,
                                        "voucher_id": voucher_customer.id,
                                        "partner_id": invoice.partner_id.id,
                                        "account_id": invoice.partner_id.property_account_receivable.id,
                                        "type": "cr",
                                        "move_line_id": invoice.move_id.line_id[0].id,
                                })
                                    
                                s_line.update({
                                        "invoice_out": outgoing_invoice.id, 
                                        "invoice_out_old": outgoing_invoice.id,
                                        "customer_payment": voucher_customer.id,
                                        "customer_payment_old": voucher_customer.id,
                                        "is_invoiced": True,                                        
                                })
                                    
                                voucher_customer.button_proforma_voucher() #funkcija od odoo (definirana vo account.voucher)
                                
                                if invoice.residual <= 0:
                                    invoice.state = 'paid' 
                                    invoice.reconciled = 'True' 
                                    invoice.residual = tmp
                                     
                                    
                    #azuriranje na balansot na vleznite fakturi (priliv na sredstva)                    
                    if line_povik_br_pobaruva != '' and line_outcome != '00000000000.00':
                        invoice_num = line_povik_br_pobaruva.rstrip()                        
                        incoming_invoice = invoices.search([('number','=', invoice_num), ('type', '=', 'in_invoice')])  
                        invoice = incoming_invoice
                        if invoice.state == 'open':
                            if invoice and invoice.residual > 0:
                                invoice.residual = invoice.residual - float(line_outcome)
                                tmp = invoice.residual               
                                payable_amount = float(line_outcome) 
                                voucher_supplier = self.env['account.voucher'].create({
                                        "name": "",
                                        "amount": payable_amount,
                                        "journal_id": self.env['account.journal'].search([('type', '=', 'bank')], limit=1).id,
                                        "account_id": invoice.partner_id.property_account_payable.id,
                                        "period_id": self.env['account.voucher']._get_period(),
                                        "partner_id": invoice.partner_id.id,
                                        "type": "payment"
                                })
                                voucher_line = self.env['account.voucher.line'].create({
                                        "name": "",                                        
                                        "amount": payable_amount,
                                        "voucher_id": voucher_supplier.id,
                                        "partner_id": invoice.partner_id.id,
                                        "account_id": invoice.partner_id.property_account_payable.id,
                                        "type": "dr",
                                        "move_line_id": invoice.move_id.line_id[0].id,
                                })
                                    
                                s_line.update({
                                        "invoice_in": incoming_invoice.id,
                                        "invoice_in_old": incoming_invoice.id,
                                        "supplier_payment": voucher_supplier.id,
                                        "supplier_payment_old": voucher_supplier.id,
                                        "is_invoiced": True,
                                })
                                    
                                voucher_supplier.button_proforma_voucher() #funkcija od odoo (definirana vo account.voucher)
                                if invoice.residual <= 0:    
                                    invoice.state = 'paid' 
                                    invoice.reconciled = 'True' 
                                    invoice.residual = tmp 
              
                    s_line.update({
                                       "statement_id": self.id,                         
                                       "income": line_income,
                                       "outcome": line_outcome, 
                                       "account_num": line_account_num,
                                       "customer_name": line_customer_name, 
                                       "customer_address": line_customer_address,
                                       "tax_num": line_tax_num,
                                       "payment_id": line_payment_id,
                                       "povik_br_dolzi": line_povik_br_dolzi,
                                       "povik_br_pobaruva": line_povik_br_pobaruva,
                                       "doznaka": line_doznaka,
                                       #'date': line_date,
                                       "br_reklamacija": line_br_reklamacija,                                                                                                  
                    })                                  
                    
                    line_num = line_num + 1 
        else:           
            raise osv.except_osv(('Error'), ('The statement does not correspond to the selected bank.'))                   
        self.hide_button = True
        return True      
       
    def show_uninvoiced_payments(self, cr, uid, ids, context=None):
        act_obj = self.pool.get('ir.actions.act_window')
        view_id = self.pool.get('ir.actions.act_window').name_search(cr, uid, name='Uninvoiced Statement Lines', context=None)
        result = act_obj.read(cr, uid, [view_id[0][0]], context=context)[0]     
        current_form = self.browse(cr, uid, ids, context=context)
        result['domain'] = "[('is_invoiced','=',False),('statement_id.id','=','"+str(current_form['id'])+"')]"
        return result
    
    def show_invoiced_payments(self, cr, uid, ids, context=None):
        act_obj = self.pool.get('ir.actions.act_window')
        view_id = self.pool.get('ir.actions.act_window').name_search(cr, uid, name='Invoiced Statement Lines', context=None)
        result = act_obj.read(cr, uid, [view_id[0][0]], context=context)[0]     
        current_form = self.browse(cr, uid, ids, context=context)        
        result['domain'] = "[('is_invoiced','=',True),('statement_id.id','=','"+str(current_form['id'])+"')]"
        return result