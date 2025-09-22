/**
 * Django Dynamic Formsets
 *
 * General logic for django-dynamic-formset.
 * static/js/jquery.formset.js
 * @author  Stan Hu
 * @version 2.1.0
 */

(function($) {
  'use strict';

  $.fn.formset = function(opts) {
    var options = $.extend({}, $.fn.formset.defaults, opts);
    var $this = $(this); // $this é o container dos forms (ex: #formset-forms)
    var $parent = $this.parent();
    var updateElementIndex = function(el, prefix, ndx) {
      var id_regex = new RegExp('(' + prefix + '-(\\d+|__prefix__)-)'),
        replacement = prefix + '-' + ndx + '-';
      if (el.attr('for')) {
        el.attr('for', el.attr('for').replace(id_regex, replacement));
      }
      if (el.attr('id')) {
        el.attr('id', el.attr('id').replace(id_regex, replacement));
      }
      if (el.attr('name')) {
        el.attr('name', el.attr('name').replace(id_regex, replacement));
      }
    };
    
    var formset_options = $this.data('formset-options');

    // Setup options for this formset
    if (formset_options) {
      options = $.extend({}, options, formset_options);
    }
    options.prefix = options.prefix || $this.data('formset-prefix');

    // The forms which are built from this formset
    var $forms = $this.find('.' + options.formCssClass);
    var totalForms = $('#id_' + options.prefix + '-TOTAL_FORMS');

    // Some useful variables
    var nextIndex = parseInt(totalForms.val(), 10);
    var maxForms = $('#id_' + options.prefix + '-MAX_NUM_FORMS').val() || '';

    // The "Add" button
    var addButton = $(options.addSelector);

    // Functions
    var hasChildElements = function(row) {
      return row.find('input,select,textarea,label,div').length > 0;
    };

    /**
     * @return {boolean}
     */
    var showAddButton = function() {
      return maxForms === '' || (maxForms - totalForms.val()) > 0;
    };

    // A função insertDeleteLink não é necessária com a abordagem do seu template,
    // mas a mantemos para integridade do plugin original.
    var insertDeleteLink = function(row) {
      var deleteButtonContainer = row.find(options.deleteContainer);
      if (deleteButtonContainer.length && row.find(options.deleteSelector).length === 0) {
          deleteButtonContainer.append(
            '<a class="' + options.deleteCssClass + '" href="javascript:void(0)">'
            + options.deleteText + '</a>'
          );
      }
    };

    $this.on('formset:add', function(event, row) {
      if (options.added) {
        options.added(row, $this);
      }
    });

    $this.on('formset:removed', function(event, row, is_checked) {
      if (options.removed) {
        options.removed(row, $this, is_checked);
      }
    });

    $forms.each(function() {
      var $form = $(this);
      if(options.deleteContainer) {
          insertDeleteLink($form);
      }
    });
    
    // Delegação de eventos para os botões de deletar
    $this.on('click', options.deleteSelector, function() {
        var row = $(this).parents('.' + options.formCssClass);
        $this.trigger('formset:removed', [row]);
        return false;
    });

    if (addButton.length) {
      if (!showAddButton()) {
        addButton.hide();
      }

      addButton.on('click', function(e) {
        e.preventDefault();
        
        var template;
        if (options.formTemplate) {
          template = (options.formTemplate instanceof $) ? options.formTemplate : $(options.formTemplate);
        } else {
          template = $('#' + options.prefix + '-empty');
        }

        var row = $(template.html()); // Usamos .html() para clonar o conteúdo interno
        row.removeClass(options.emptyCssClass)
          .addClass(options.formCssClass);

        if (hasChildElements(row)) {
          row.find('*').each(function() {
            updateElementIndex($(this), options.prefix, nextIndex);
          });

          // =======================================================================
          // CORREÇÃO PRINCIPAL AQUI:
          // A nova linha (row) deve ser adicionada ao container do formset ($this),
          // e não antes do botão "Adicionar".
          // =======================================================================
          $this.append(row);
          // =======================================================================
          
          totalForms.val(parseInt(totalForms.val(), 10) + 1);
          nextIndex++;
        }

        if (!showAddButton()) {
          addButton.hide();
        }
        
        // Dispara o evento de adição
        $this.trigger('formset:add', [row, $this]);

        return false;
      });
    }

    return this;
  };


  /* Setup plugin defaults */
  $.fn.formset.defaults = {
    prefix: 'form', 
    formCssClass: 'dynamic-form', 
    deleteCssClass: 'delete-row', 
    deleteText: 'Remove', 
    deleteContainer: null, 
    deleteSelector: '.delete-row',
    addCssClass: 'add-row', 
    addSelector: null, 
    addText: 'Add another', 
    emptyCssClass: 'empty-form', 
    formTemplate: null, 
    hideRemoved: true,
    removed: null, 
    added: null, 
  };
})(jQuery);