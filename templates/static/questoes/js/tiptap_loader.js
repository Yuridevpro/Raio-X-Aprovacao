import { Editor } from 'https://esm.sh/@tiptap/core';
import StarterKit from 'https://esm.sh/@tiptap/starter-kit';
import { Markdown } from 'https://esm.sh/tiptap-markdown';
import Underline from 'https://esm.sh/@tiptap/extension-underline';

// Anexa tudo ao objeto global 'window' para ser acessível no SCRIPT de inicialização
window.TipTap = {
    Editor,
    StarterKit,
    Markdown,
    Underline,
};