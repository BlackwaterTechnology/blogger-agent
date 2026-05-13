(function(){
    try {
        const editor = document.querySelector('.ProseMirror');
        if (!editor) return 'no editor';
        const captions = []; // mocked
        const isEmptyP = el => {
            if (!el || (el.tagName !== 'P' && el.tagName !== 'SECTION')) return false;
            if (el.querySelector('img, pre, table, ul, ol, blockquote, hr')) return false;
            const txt = (el.innerText || '').replace(/[\u200B-\u200D\uFEFF]/g, '').trim();
            return txt.length === 0;
        };
        const captionStyle = 'text-align:center; font-size:13px; color:#888888; line-height:1.6; margin:6px 0 14px; padding:0 8px;';
        let captioned = 0, removed = 0;
        
        // Use a function to get current images safely
        const getImgs = () => Array.from(editor.querySelectorAll('img.wxw-img'));
        
        const initialImgsCount = getImgs().length;
        
        for (let i = 0; i < initialImgsCount; i++) {
            const currentImgs = getImgs();
            if (i >= currentImgs.length) break;
            
            let top = currentImgs[i];
            while (top.parentElement && top.parentElement !== editor) top = top.parentElement;
            
            const caption = (captions[i] || '').trim();
            
            let emptyCount = 0;
            let curr = top.nextElementSibling;
            while (curr && isEmptyP(curr)) {
                emptyCount++;
                curr = curr.nextElementSibling;
            }
            
            let isLast = false;
            if (emptyCount > 0) {
                let lastEmpty = top;
                for(let j=0; j<emptyCount; j++) lastEmpty = lastEmpty.nextElementSibling;
                if (!lastEmpty.nextElementSibling) isLast = true;
            }
            
            if (emptyCount > 0) {
                let keepCount = caption ? 1 : 0;
                if (isLast && emptyCount > keepCount) {
                    keepCount++; 
                }
                
                let deleteCount = emptyCount - keepCount;
                
                for (let d = 0; d < deleteCount; d++) {
                    let toDelete = top;
                    for (let j = 0; j <= keepCount; j++) {
                        if (toDelete) toDelete = toDelete.nextElementSibling;
                    }
                    if (toDelete) {
                        editor.focus();
                        const sel = window.getSelection();
                        const range = document.createRange();
                        range.selectNode(toDelete);
                        sel.removeAllRanges();
                        sel.addRange(range);
                        if (document.execCommand('delete')) {
                            removed++;
                        }
                    }
                }
                
                if (caption) {
                    let target = top.nextElementSibling;
                    if (target && isEmptyP(target)) {
                        editor.focus();
                        const sel = window.getSelection();
                        const range = document.createRange();
                        range.selectNodeContents(target);
                        sel.removeAllRanges();
                        sel.addRange(range);
                        document.execCommand('insertText', false, caption);
                        target.setAttribute('style', captionStyle);
                        captioned++;
                    }
                }
            }
        }
        return JSON.stringify({captioned, removed});
    } catch(e) { return 'err: ' + e.message; }
})();
