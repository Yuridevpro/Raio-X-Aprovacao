
    // Importa os módulos principais
    import { Editor } from 'https://esm.sh/@tiptap/core'
    import StarterKit from 'https://esm.sh/@tiptap/starter-kit'
    import { Markdown } from 'https://esm.sh/tiptap-markdown'

    // Importa as NOVAS extensões que vamos usar
    import Underline from 'https://esm.sh/@tiptap/extension-underline'
   

    // Anexa tudo ao objeto global 'window' para ser acessível no SCRIPT 2
    window.TipTap = {
        Editor,
        StarterKit,
        Markdown,
        Underline,
    };

