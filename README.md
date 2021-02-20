# CudaText addon. Extended double-click selection
A plugin to streamline the introduction of copy-paste bugs.  
Adds to usual double-click selection:  
* Shift+Double-click: includes additional characters to selection
* Shift+Triple-click: "expression selection" (useful for selecting function call with arguments)  
![demo](/readme/selection_example.png)
        
## Configuration
Plugin has options in the config file, call menu item  
"Options / Settings-plugins / Extended Selection":  
* "include_chars": additional characters to include in Shift+double-click selection
* "stop_ext": characters to stop Shift+triple-click selection when not enclosed in ()[]{}<>
* "open_chars" and "close_chars": map of opening-to-closing and closing-to-opening brackets. Used to limit selection extension to stay within brackets. And to ignore "stop_ext" characters inside brackets, when they follow selected text. 

For example when `cc` clicked in following line:  
    `aa = bb.cc<dd>(ee=ff) = ww`
	
* normal double-click will yield selection:  
    `cc`  
* addon's shift+double-click:  
    `bb.cc`  
  > (period and adjacent text is added to selection because '.' is in the "include_chars" for this lexer)
* addon's shift+triple-click:  
    `bb.cc<dd>(ee=ff)`  
	> (selection stops at equal-signs at both sides because '=' is in the "stop_ext" for this lexer. "stop_ext" characters ('=' here) are ignored inside brackets)