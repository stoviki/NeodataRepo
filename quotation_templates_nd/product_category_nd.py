from openerp.osv import osv, fields
from openerp import models, api, tools

class product_category_nd(models.Model):
    _inherit = 'product.category'
    
    def _get_image(self, cr, uid, ids, name, args, context=None):
        result = dict.fromkeys(ids, False)
        for obj in self.browse(cr, uid, ids, context=context):
            result[obj.id] = tools.image_get_resized_images(obj.image, avoid_resize_medium=True)
        return result
    
    def _set_image(self, cr, uid, id, name, value, args, context=None):
        return self.write(cr, uid, [id], {'image': tools.image_resize_image_big(value)}, context=context)
    
    _columns={
              'category_description': fields.html('Category Description', translate=True,
                                      help="A precise description of the Category."),
              
              'image': fields.binary("Image", help="This field holds the image used as image for the product category, limited to 1024x1024px."),
              'image_medium': fields.function(_get_image, fnct_inv=_set_image,
                                              string="Medium-sized image", type="binary", multi="_get_image", 
                                              store={
                                                     'product.category': (lambda self, cr, uid, ids, c={}: ids, ['image'], 10),
                                              },
                                              help="Medium-sized image of the category. It is automatically "\
                                                   "resized as a 128x128px image, with aspect ratio preserved, "\
                                                   "only when the image exceeds one of those sizes. Use this field in form views or some kanban views."),
    }