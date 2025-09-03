document.addEventListener('DOMContentLoaded', function () {
    // Espera o TipTap ser carregado pelo loader
    if (!window.TipTap) {
        console.error("Tiptap loader não foi executado a tempo.");
        return;
    }

    const { Editor, StarterKit, Markdown, Underline } = window.TipTap;

    // Encontra todos os textareas ocultos que devem ser transformados em editores
    const textareas = document.querySelectorAll('.tiptap-hidden-textarea');

    textareas.forEach(textarea => {
        const container = textarea.closest('.tiptap-admin-container');
        if (!container) return;

        const editorElement = container.querySelector('.tiptap-editor');
        const toolbar = container.querySelector('.tiptap-toolbar');
        const initialContent = textarea.value;

        const editor = new Editor({
            element: editorElement,
            extensions: [
                StarterKit,
                Underline,
                Markdown.configure({ html: false, linkify: true, breaks: true }),
            ],
            content: initialContent,
            
            // ESSENCIAL: Sincroniza o conteúdo do editor com o textarea oculto
            onUpdate: ({ editor }) => {
                textarea.value = editor.storage.markdown.getMarkdown();
            },
        });

        // Adiciona funcionalidade aos botões da barra de ferramentas
        toolbar.querySelectorAll('button[data-command]').forEach(button => {
            button.addEventListener('click', () => {
                const command = button.dataset.command;
                const commands = {
                    toggleBold: () => editor.chain().focus().toggleBold().run(),
                    toggleItalic: () => editor.chain().focus().toggleItalic().run(),
                    toggleUnderline: () => editor.chain().focus().toggleUnderline().run(),
                    toggleBulletList: () => editor.chain().focus().toggleBulletList().run(),
                    toggleOrderedList: () => editor.chain().focus().toggleOrderedList().run(),
                };
                if (commands[command]) {
                    commands[command]();
                }
            });

            // Atualiza o estado (ativo/inativo) do botão
            editor.on('transaction', () => {
                const command = button.dataset.command.replace('toggle', '').toLowerCase();
                button.classList.toggle('active', editor.isActive(command));
            });
        });
    });
});