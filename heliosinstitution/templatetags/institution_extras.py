from django import template

register = template.Library()


@register.filter("slice_institutions", is_safe=True)
def slice_institutions(value, arg):
    """
    Returns a list sliced in two.
    """
    try:
    	if arg == '1':	
        	return value[0:len(value)//2+1]
        if arg == '2':
        	return value[len(value)//2+1:len(value)]
    except (ValueError, TypeError):
        return value # Fail silently.


@register.inclusion_tag('dropdown.html', takes_context=True)
def dropdown(context):
	elections = context['elections']
	values = []

	if context['drop_type'] == 'year' and elections:
		last_year = elections[0].created_at.year
		first_year = elections[len(elections)-1].created_at.year
		values = []
		for year in range(int(first_year), int(last_year)+1):
			values.append(year)

	return {
		'values': values,
		'drop_type': context['drop_type'],
		}
