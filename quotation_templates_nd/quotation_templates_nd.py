from openerp.osv import osv, fields
from openerp import models, api, tools
from openerp.tools.translate import _

class quotation_templates_nd(models.Model):
    _name = 'quotation.templates.nd'    
    
    def _get_image(self, cr, uid, ids, name, args, context=None):
        result = dict.fromkeys(ids, False)
        for obj in self.browse(cr, uid, ids, context=context):
            result[obj.id] = tools.image_get_resized_images(obj.image, avoid_resize_medium=True)
        return result
    
    def _set_image(self, cr, uid, id, name, value, args, context=None):
        return self.write(cr, uid, [id], {'image': tools.image_resize_image_big(value)}, context=context)   
    
    _columns = {
                'name': fields.char("Name", required=True),
                'external_id': fields.char("Technical Name", required=True),
                'qweb_header': fields.text("Report Header"),
                'qweb_content': fields.text("Report Content", required=True),
                'qweb_footer': fields.text("Report Footer"),
                'image': fields.binary("Image", help="This field holds the image used as image for the quotation template, limited to 1024x1024px."),
                'image_medium': fields.function(_get_image, fnct_inv=_set_image,
                                                string="Medium-sized image", type="binary", multi="_get_image", 
                                                store={
                                                     'quotation.templates.nd': (lambda self, cr, uid, ids, c={}: ids, ['image'], 10),
                                                },
                                                help="Medium-sized image of the quotation template. It is automatically "\
                                                   "resized as a 128x128px image, with aspect ratio preserved, "\
                                                   "only when the image exceeds one of those sizes. Use this field in form views or some kanban views."),                
                
                'description':  fields.text("Description"),
                'selected': fields.boolean("Selected"),
                
    }
    
    _defaults = {
        'selected': False,        
        'qweb_header': '<div clas="header">'+'\n'+'</div>',
        'qweb_content': '<div clas="page">'+'\n'+'<div clas="oe_structure">'+'\n'+'</div>'+'\n'+'</div>', 
        'qweb_footer':  '<div clas="footer">'+'\n'+'</div>',
    }
    
    @api.multi
    def preview_template(self):        
        views = self.env['ir.ui.view']
        view_id = views.search([('name','=','view.image.form')])[0]
                
        return {
                'type': 'ir.actions.act_window',
                'name': _('Template Preview'),
                'res_model': 'quotation.templates.nd',
                'view_type': 'form',
                'view_id': view_id.id,
                'view_mode': 'form',
                'res_id': self.id,
                'target' : 'new',
        }         
   
    @api.multi
    def select_template(self):  
        templates = self.search([])
        
        for template in templates:            
            if(template.selected):
                template.selected = False                
        self.selected = True   
       
                  
        header_template_id = self.env.ref('quotation_templates_nd.quotation_template_header')
        content_template_id = self.env.ref('quotation_templates_nd.report_quotation_template_document')        
        footer_template_id = self.env.ref('quotation_templates_nd.quotation_template_footer')     
        for template in templates:            
            if(template.selected):                
                header = template.qweb_header
                content = template.qweb_content
                footer = template.qweb_footer
                
                # Kod za postavuvanje header
                header_arch = '''<?xml version="1.0"?>
                                 <data inherit_id="report.external_layout_header">
                                     <xpath expr="//div[@class='header']" position="replace">'''   
                header_arch = header_arch + header                      
                header_arch = header_arch + '''</xpath></data>'''
                header_template_id.arch = header_arch
               
                # Kod za postavuvanje glavna sodrzina
                content_arch = '''<?xml version="1.0"?>
                                  <data inherit_id="sale.report_saleorder_document">
                                      <xpath expr="//div[@class='page']" position="replace">'''   
                content_arch = content_arch + content                      
                content_arch = content_arch + '''</xpath></data>'''
                content_template_id.arch = content_arch
                
                # Kod za postavuvanje footer
                footer_arch = '''<?xml version="1.0"?>
                                 <data inherit_id="report.external_layout_footer">
                                     <xpath expr="//div[@class='footer']" position="replace">'''   
                footer_arch = footer_arch + footer                      
                footer_arch = footer_arch + '''</xpath></data>'''
                footer_template_id.arch = footer_arch                            
                
        return {                
                'type': 'ir.actions.client',
                'tag': 'reload'                
        } 
        
    @api.multi
    def unlink(self):
        templates = self.env['quotation.templates.nd'].browse(self.ids)
        print templates
        for template in templates:
            if(not template.selected):
                super(quotation_templates_nd, template).unlink()                
            else:
                raise osv.except_osv(('Error'), ('You can not delete a selected template.'+'\n'+
                                             'Please select another template first, and try again.'))   
   
   
    