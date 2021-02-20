import os
import re
import time
import json

from cudatext import *

from cudax_lib import get_translation
_   = get_translation(__file__)  # I18N

fn_config = os.path.join(app_path(APP_DIR_SETTINGS), 'cuda_extended_selection.json')

click_time = 0.3 # sec

_config_json = """
  {
    "_comment_a":"default and lexer-specific settings",
    "_comment_b":"include_chars: additional characters to include in Shift+double-click selection",
    "_comment_c":"stop_ext: characters to stop Shift+triple-click selection when not enclosed in ()[]{}<>",

    "default":{
      "include_chars":".",
      "stop_ext":"=,",
      "open_chars":{
        "(":")", "[":"]", "{":"}", "<":">"
      },
      "close_chars":{
        ")":"(", "]":"[", "}":"{", ">":"<"
      }
    },
    "Python,C#":{
      "include_chars":".",
      "stop_ext":"=,"
    }
  }
"""
OPEN_CHARS    = {'default':{'(':')', '[':']', '{':'}', '<':'>'}}
CLOSE_CHARS   = {'default':{')':'(', ']':'[', '}':'{', '>':'<'}} # NOTE:map function used when swapped
INCLUDE_CHARS = {'default':'.'} # {'default':{'include_chars':'.', 'stop_ext':'=,'}, 'Python,C#':'.'}
STOP_EXT      = {'default':'=,'}

class Command:
    
    def __init__(self):
        self.to_sel = None
        self.triple_sel = None
        self.skip_caret = False
        
        self.load_config()
 
 
    def config(self):
      if not os.path.isfile(fn_config):
        with open(fn_config, 'w') as f:
          f.write(_config_json)
      file_open(fn_config)
        
      
    def on_click_dbl(self, ed_self, state):
      """ store modified selection to be applied in on_caret()
      """
      if state == 'sL'  or  state == 'Ls': # only shift and left mouse are pressed 
        self.calc_selections()
        
        
    def menu_entry(self):
      """ if no selection and no stored: calculate selections  and  apply once
      """
      if not self.triple_sel:
        self.calc_selections()
      self.apply_selection(ignore_time=True)
      
      
    def calc_selections(self):
      lex = ed.get_prop(PROP_LEXER_CARET) 
      comment_str = lexer_proc(LEXER_GET_PROP, lex)["c_line"]  if lex else  ''
         
      include_chars = INCLUDE_CHARS.get(lex, INCLUDE_CHARS['default']) 
      incl_pattern = '^[\w'+include_chars+']*'
      
      caret_x, caret_y = ed.get_carets()[0][:2]
      
      l = 0
      textl = ed.get_text_substr( max(0, caret_x-255), caret_y,   caret_x, caret_y )
      lmatch = re.search(incl_pattern, textl[::-1])
      if lmatch:
        l = lmatch.end()

      r = 0
      textr = ed.get_text_substr(caret_x, caret_y, caret_x+255, caret_y)
      if comment_str:
        textr = textr.split(comment_str, 1)[0]  # stop selection at comment string
      rmatch = re.search(incl_pattern, textr)
      if rmatch:
        r = rmatch.end()
        
      open_chars = OPEN_CHARS.get(lex, OPEN_CHARS['default'])
      close_chars = CLOSE_CHARS.get(lex, CLOSE_CHARS['default'])
          
      if l > 0 or r > 0:
        x1 = caret_x-l
        x2 = caret_x+r
        # store expanded double click selection to apply later
        self.to_sel = (x1,caret_y, x2,caret_y)  
        
      clicked_bracket = textr and (textr[0] in open_chars  or  textr[0] in close_chars)
      if l > 0  or  r > 0  or  clicked_bracket: 
        expr_l = self.get_expression_sel(textl, lex, reverse=True)
        expr_r = self.get_expression_sel(textr, lex)
        # store expanded triple click selection to apply later (-if third click comes)
        self.triple_sel = [time.time()+click_time,  caret_x-len(expr_l), caret_y,  caret_x+len(expr_r), caret_y]
          
          
    def get_expression_sel(self, s, lex, reverse=False): 
      """extract part from string that matches 'expression' rules
      """
      open_chars = OPEN_CHARS.get(lex, OPEN_CHARS['default'])
      close_chars = CLOSE_CHARS.get(lex, CLOSE_CHARS['default'])
      stop_ext = set(STOP_EXT.get(lex, STOP_EXT['default']))
      
      if reverse:
        s = s[::-1]
        open_chars,close_chars = close_chars,open_chars # swap
      
      lvls = {ch:0 for ch in open_chars}
      for i,ch in enumerate(s):
        if ch in open_chars: # '..(' # for backward: use closing
          lvls[ch] += 1
          
        elif ch in close_chars: # '..)' '..(..)'
          open_char = close_chars[ch]
          if lvls[open_char] <= 0: # enclosing end - stop: '..)'
            s = s[:i].rstrip()
            break
          else:
            lvls[open_char] -= 1 # '..(..)'
        
        elif ch in stop_ext  and  all(level == 0 for level in lvls.values()): # stop char is not inside any brackets - stop
          s = s[:i].rstrip()
          break
      
      if reverse:
        return s[::-1].lstrip()
      
      return s.rstrip()
        
          
    def on_caret(self, ed_self):
      """apply stored selection for Shift+double/triple click
      """
      # expanding double-click causes extra on_caret() - skip
      if self.skip_caret:
        self.skip_caret = False
        return
        
      self.apply_selection(ed_self)
      

    def apply_selection(self, ed_self=None, ignore_time=False):
      if self.to_sel:
        x1,y1, x2,y2 = self.to_sel
        self.to_sel = None
        self.skip_caret = True
        ed.set_sel_rect(x1, y1,  x2, y2)

      elif self.triple_sel:
        if self.triple_sel[0] >= time.time()  or  ignore_time:
          x1,y1, x2,y2 = self.triple_sel[1:5]
          self.triple_sel = None # needs to be before set_sel_rect()
          ed.set_sel_rect(x1, y1,  x2, y2)
          
        self.triple_sel = None
        
        
    def load_config(self):
      global OPEN_CHARS, CLOSE_CHARS, STOP_EXT, INCLUDE_CHARS

      # store initial prefs, restore on exception
      open_chars, close_chars, stop_ext, include_chars = OPEN_CHARS, CLOSE_CHARS, STOP_EXT, INCLUDE_CHARS
      OPEN_CHARS, CLOSE_CHARS, STOP_EXT, INCLUDE_CHARS = {},{},{},{}

      try:
        if not os.path.isfile(fn_config):
          print(_('Extended double-click selection: Missing config file. Creating a default one.'))
          with open(fn_config, 'w') as f:
            f.write(_config_json)

        with open(fn_config, 'r') as f:
          j = json.load(f)

          # default
          jd = j['default']
          OPEN_CHARS    = {'default':jd['open_chars'] }
          CLOSE_CHARS   = {'default':jd['close_chars'] }
          INCLUDE_CHARS = {'default':jd['include_chars'] }
          STOP_EXT      = {'default':jd['stop_ext'] }

          # lexers
          for key,val in j.items():
            if key[0] == '_' or key == 'default': 
              continue

            for lex in key.split(','):
              if not lex:
                continue

              OPEN_CHARS[lex]     = val.get('open_chars', OPEN_CHARS['default']) 
              CLOSE_CHARS[lex]    = val.get('close_chars', CLOSE_CHARS['default']) 
              INCLUDE_CHARS[lex]  = val.get('include_chars', INCLUDE_CHARS['default']) 
              STOP_EXT[lex]       = val.get('stop_ext', STOP_EXT['default']) 

      except Exception as e:
        OPEN_CHARS, CLOSE_CHARS, STOP_EXT, INCLUDE_CHARS = open_chars, close_chars, stop_ext, include_chars

        print(_('Extended Mouse Selection: Failed to load config, using defaults'))
        print(_(' - Error:{}: ').format(type(e))) # 'raise' here is not printed
