{
    'name': 'Quotation Templates',        
    'application': True,
    'author': 'NeoData',
    'depends': ['report', 'sale', 'product', 'base', 'web'],    
    'data': [
             'security/ir.model.access.csv',             
             'product_category_nd_view.xml',             
             'image_view.xml',
             'quotation_templates_nd_view.xml',
             'templates/quotation_report_template.xml',
             'templates/default_odoo_template.xml',
             'templates/neodata_template.xml',
             'templates/product_categories_quotation.xml',
             'templates/product_categories_img_quotation.xml',             
             'templates/neodata_template_2.xml'                          
             ],      
    'summary': 'Different quotation templates that you can choose from.',
    'category': 'Sales Management',
    'price': 50.00,
    'currency': 'EUR',
    
}