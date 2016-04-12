# -*- coding: utf-8 -*-
from openerp.osv import osv, fields
from openerp import models, api
import os
import base64
import logging

_logger = logging.getLogger(__name__)
    
class bank_statement_line(models.Model):   
    _name = 'bank.statement.line'
    _columns = {
                'statement_id': fields.many2one('bank.statements.custom', 'Bank Statement Reference', ondelete='cascade'),
                'instrument': fields.char('Instrument'),
                'income': fields.float('Income'),
                'outcome': fields.float('Outcome'),
                'account_id': fields.many2one('account.account', 'Account ID', select=1),
                'account_num': fields.char('Account'),
                'customer_id': fields.many2one('res.partner', 'Customer', select=1),  # ima info i za naziv i za sediste na nalogodavac/nalogoprimac                        
                'customer_name': fields.char('Customer Name'), # naziv na nalogodavac/nalogoprimac
                'customer_address': fields.char('Customer Address'), # sediste na nalogodavac/nalogoprimac
                'tax_num': fields.char('Tax Number'),  # danocen broj
                'payment_id': fields.char('Payment Code'),  # sifra na plakanje - dali e ista so id na plakjanje
                'povik_br_dolzi': fields.char('Outgoing Invoice Number'),
                'povik_br_pobaruva': fields.char('Incoming Invoice Number'),  
                'doznaka': fields.char('Description'),
                'date': fields.date('Date'),
                'br_reklamacija': fields.char('Reclamation Number'),
                'invoice_out': fields.many2one('account.invoice', 'Customer Invoice', select='1'),
                'invoice_out_old': fields.many2one('account.invoice'),
                'invoice_in': fields.many2one('account.invoice', 'Supplier Invoice', select='1'), 
                'invoice_in_old': fields.many2one('account.invoice'),                  
                'customer_payment': fields.many2one('account.voucher', 'Customer Payment', select='1'), #plakjanje od kupuvach             
                'customer_payment_old': fields.many2one('account.voucher'),
                'supplier_payment': fields.many2one('account.voucher', 'Supplier Payment', select='1'), #plakjanje kon dobavuvach                     
                'supplier_payment_old': fields.many2one('account.voucher'),
                'is_invoiced': fields.boolean('Is Invoiced'), 
    }     
         
    _defaults = {
              "is_invoiced": False,                                      
    }
    
    #metod za promena na fakturata koja se plakja so soodvetnata stavka
    #starata faktura se predava kako atribut, za da moze da se izbrise plakjanjeto od nea  
    
    @api.one
    def update_invoices(self): 
        #dokolku niedna izlezna faktura ne e povrzana momentalno
        if (not self.invoice_out_old) and self.invoice_out.state=='open' and self.income != '00000000000.00':
            invoice = self.invoice_out            
            if invoice and invoice.residual > 0:
                invoice.residual = invoice.residual - float(self.income)
                tmp = invoice.residual
                payable_amount = float(self.income) # The amount you want to pay                                    
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
                                    
                self.update({
                                        "invoice_out": invoice.id, 
                                        "invoice_out_old": invoice.id,
                                        "customer_payment": voucher_customer.id,
                                        "customer_payment_old": voucher_customer.id,
                                        "is_invoiced": True,
                })
                voucher_customer.button_proforma_voucher() #funkcija od odoo (definirana vo account.voucher)
                if invoice.residual <= 0: 
                    invoice.state = 'paid' 
                    invoice.reconciled = 'True' 
                    invoice.residual = tmp  
                    
        #dokolku niedna vlezna faktura ne e povrzana momentalno
        if (not self.invoice_in_old) and self.invoice_in.state=='open' and self.outcome != '00000000000.00':
            invoice = self.invoice_in 
            print invoice.number                   
            if invoice and invoice.residual > 0:
                invoice.residual = invoice.residual - float(self.outcome)
                tmp = invoice.residual               
                payable_amount = float(self.outcome) 
                voucher_supplier = self.env['account.voucher'].create({
                                        "name": "",
                                        "number": self.supplier_payment_old.number,
                                        "amount": payable_amount,
                                        "journal_id": self.env['account.journal'].search([('type', '=', 'bank')], limit=1).id,
                                        "account_id": invoice.partner_id.property_account_payable.id,
                                        "period_id": self.env['account.voucher']._get_period(),
                                        "partner_id": invoice.partner_id.id,
                                        "type": "payment"
                })
                                           
                voucher_line_supplier = self.env['account.voucher.line'].create({
                                        "name": "",                                        
                                        "amount": payable_amount,
                                        "voucher_id": voucher_supplier.id,
                                        "partner_id": invoice.partner_id.id,
                                        "account_id": invoice.partner_id.property_account_payable.id,
                                        "type": "dr",
                                        "move_line_id": invoice.move_id.line_id[0].id,
                })
                                        
                voucher_supplier.button_proforma_voucher() #funkcija od odoo (definirana vo account.voucher)
                                
                self.update({                                     
                                     "invoice_in": invoice.id, 
                                     "invoice_in_old": invoice.id,
                                     "supplier_payment": voucher_supplier.id,
                                     "supplier_payment_old": voucher_supplier.id,  
                                     "is_invoiced": True,                                
                })
                    
                #se zatvora novata faktura
                if invoice.residual <= 0:
                    invoice.update({
                       "state": "paid", 
                       "reconciled": True, 
                       "residual": tmp              
                })                       
                                             
        #dokolku nastanala promena na izlezna faktura se azurira balansot na novata faktura
        if self.invoice_out != self.invoice_out_old and self.invoice_out.state=='open' and self.income != '00000000000.00':                
            invoice = self.invoice_out
            if invoice and invoice.residual > 0:
                invoice.residual = invoice.residual - float(self.income)
                tmp = invoice.residual                   
                payable_amount = float(self.income) #Iznosot sto e platen                              
                #se otvora starata faktura
                self.invoice_out_old.update({
                       "state": "open", 
                       "reconciled": False,  
                       "residual": self.invoice_out_old.residual+self.customer_payment_old.amount                                                         
                })
                    
                #se brisi staroto plakjanje
                move_old = self.env['account.move'].search([('id', '=', self.customer_payment_old.move_id.id)])                
                voucher_line_old = self.env['account.voucher.line'].search([('voucher_id', '=', self.customer_payment_old.id)])
                    
                voucher_line_old.unlink()
                self.customer_payment_old.state = 'draft'
                self.customer_payment_old.unlink()                    
                
                line = self.invoice_out_old.payment_ids[0]                
                line.invoice = ''
                line.unlink()
                
                move_old.state = 'draft'  
                move_old.unlink()
                        
                voucher_customer = self.env['account.voucher'].create({
                                        "name": "",
                                        "number": self.customer_payment_old.number,
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
                                        
                voucher_customer.button_proforma_voucher() #funkcija od odoo (definirana vo account.voucher)
                    
               
                self.update({                                     
                            "invoice_out": invoice.id, 
                            "invoice_out_old": invoice.id,
                            "customer_payment": voucher_customer.id,
                            "customer_payment_old": voucher_customer.id, 
                            "is_invoiced": True,                                
                })
                    
                #se zatvora novata faktura
                if invoice.residual <= 0:
                    invoice.update({
                       "state": "paid", 
                       "reconciled": True, 
                       "residual": tmp              
                    }) 
                    
        #dokolku nastanala promena na vlezna faktura se azurira balansot na novata faktura
        if self.invoice_in != self.invoice_in_old and self.invoice_in.state=='open' and self.outcome != '00000000000.00':                
            invoice = self.invoice_in
            if invoice and invoice.residual > 0:
                invoice.residual = invoice.residual - float(self.outcome)
                tmp = invoice.residual                   
                payable_amount = float(self.outcome) #Iznosot sto e platen                              
                #se otvora starata faktura
                self.invoice_in_old.update({
                       "state": 'open', 
                       "reconciled": 'False',
                       "residual": self.invoice_in_old.residual+self.supplier_payment_old.amount                                                           
                })
                    
                #se brisi staroto plakjanje
                move_old = self.env['account.move'].search([('id', '=', self.supplier_payment_old.move_id.id)])
                
                voucher_line_old = self.env['account.voucher.line'].search([('voucher_id', '=', self.supplier_payment_old.id)])
                    
                voucher_line_old.unlink()
                self.supplier_payment_old.state = 'draft'
                self.supplier_payment_old.unlink()
                
                line = self.invoice_in_old.payment_ids[0]                
                line.invoice = ''
                line.unlink()                    
               
                move_old.state = 'draft'  
                move_old.unlink()
                        
                voucher_supplier = self.env['account.voucher'].create({
                                        "name": "",
                                        "number": self.supplier_payment_old.number,
                                        "amount": payable_amount,
                                        "journal_id": self.env['account.journal'].search([('type', '=', 'bank')], limit=1).id,
                                        "account_id": invoice.partner_id.property_account_payable.id,
                                        "period_id": self.env['account.voucher']._get_period(),
                                        "partner_id": invoice.partner_id.id,
                                        "type": "payment"
                })
                                           
                voucher_line_supplier = self.env['account.voucher.line'].create({
                                        "name": "",                                        
                                        "amount": payable_amount,
                                        "voucher_id": voucher_supplier.id,
                                        "partner_id": invoice.partner_id.id,
                                        "account_id": invoice.partner_id.property_account_payable.id,
                                        "type": "dr",
                                        "move_line_id": invoice.move_id.line_id[0].id,
                })
                                        
                voucher_supplier.button_proforma_voucher() #funkcija od odoo (definirana vo account.voucher)
                                
                self.update({                                     
                                     "invoice_in": invoice.id, 
                                     "invoice_in_old": invoice.id,
                                     "supplier_payment": voucher_supplier.id,
                                     "supplier_payment_old": voucher_supplier.id,  
                                     "is_invoiced": True,                                
                })
                    
                #se zatvora novata faktura
                if invoice.residual <= 0:
                    invoice.update({
                       "state": "paid", 
                       "reconciled": True, 
                       "residual": tmp              
                }) 
                    
        