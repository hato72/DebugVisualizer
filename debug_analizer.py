import ast
import sys
import graphviz
from functools import wraps

class DebugFlowVisualizer:
    def __init__(self):
        self.dot = graphviz.Digraph(comment='Debug Flow', format='svg')
        self.node_count = 0
        self.current_function = None
        self.execution_path = []
        self.loop_stack = []

    def instrument_file(self, filename):
        with open(filename, 'r') as file:
            tree = ast.parse(file.read())
        
        transformer = DebugTransformer()
        modified_tree = transformer.visit(tree)
        
        modified_code = ast.unparse(modified_tree)
        
        exec(modified_code, globals())

    def add_node(self, label, result=None, shape='box'):
        node_id = f'node_{self.node_count}'
        if result is not None:
            label += f'\nResult: {result}'
        self.dot.node(node_id, label, shape=shape)
        self.node_count += 1
        if self.execution_path:
            self.dot.edge(self.execution_path[-1], node_id)
        self.execution_path.append(node_id)
        return node_id

    def start_function(self, func_name, args, kwargs):
        self.current_function = func_name
        args_str = ', '.join([f'{k}={v!r}' for k, v in kwargs.items()] + [repr(arg) for arg in args])
        self.add_node(f'Function: {func_name}({args_str})', shape='ellipse')

    def end_function(self, result):
        self.add_node(f'Return: {result!r}', shape='diamond')
        self.current_function = None

    def start_loop(self, loop_info):
        self.add_node(f'Loop Start: {loop_info}', shape='parallelogram')

    def loop_iteration(self, iteration):
        self.add_node(f'Loop Iteration: {iteration}', shape='parallelogram')

    def end_loop(self):
        self.add_node('Loop End', shape='parallelogram')

    def add_condition(self, condition, result):
        self.add_node(f'Condition: {condition}', result, shape='diamond')

    def add_variable(self, var_name, value):
        self.add_node(f'Variable: {var_name} = {value!r}', shape='plaintext')

    def add_print(self, content):
        self.add_node(f'Print: {content}', shape='oval')

    def add_if_branch(self, condition, branch):
        self.add_node(f'If Branch: {condition}\nTaken: {branch}', shape='diamond')

    def render(self, output_file):
        self.dot.render(output_file, view=True)

visualizer = DebugFlowVisualizer()

def debug_function(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        visualizer.start_function(func.__name__, args, kwargs)
        result = func(*args, **kwargs)
        visualizer.end_function(result)
        return result
    return wrapper

def debug_loop(loop_info):
    visualizer.start_loop(loop_info)

def debug_loop_iteration(iteration):
    visualizer.loop_iteration(iteration)

def debug_loop_end():
    visualizer.end_loop()

def debug_condition(condition):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            result = func(*args, **kwargs)
            visualizer.add_condition(condition, result)
            return result
        return wrapper
    return decorator

def debug_variable(var_name, value):
    visualizer.add_variable(var_name, value)

def debug_print(*args, **kwargs):
    content = ' '.join(repr(arg) for arg in args)
    visualizer.add_print(content)
    print(*args, **kwargs)

def debug_if_branch(condition, branch):
    visualizer.add_if_branch(condition, branch)

class DebugTransformer(ast.NodeTransformer):
    def visit_FunctionDef(self, node):
        node.decorator_list.append(ast.Name(id='debug_function', ctx=ast.Load()))
        self.generic_visit(node)
        return node

    def visit_For(self, node):
        loop_info = f'{ast.unparse(node.target)} in {ast.unparse(node.iter)}'
        new_body = [
            ast.Expr(ast.Call(
                func=ast.Name(id='debug_loop', ctx=ast.Load()),
                args=[ast.Constant(value=loop_info)],
                keywords=[]
            )),
            ast.Expr(ast.Call(
                func=ast.Name(id='debug_loop_iteration', ctx=ast.Load()),
                args=[node.target],
                keywords=[]
            ))
        ] + node.body + [
            ast.Expr(ast.Call(
                func=ast.Name(id='debug_loop_end', ctx=ast.Load()),
                args=[],
                keywords=[]
            ))
        ]
        node.body = new_body
        self.generic_visit(node)
        return node

    def visit_If(self, node):
        condition = ast.unparse(node.test)

        # 条件のデバッグ呼び出し
        debug_condition_call = ast.Expr(ast.Call(
            func=ast.Name(id='debug_condition', ctx=ast.Load()),
            args=[ast.Constant(value=condition)],
            keywords=[]
        ))

        # Trueブランチの前にデバッグ情報を追加
        true_branch_debug = ast.Expr(ast.Call(
            func=ast.Name(id='debug_if_branch', ctx=ast.Load()),
            args=[ast.Constant(value=condition), ast.Constant(value='True')],
            keywords=[]
        ))

        # Falseブランチの前にデバッグ情報を追加
        false_branch_debug = ast.Expr(ast.Call(
            func=ast.Name(id='debug_if_branch', ctx=ast.Load()),
            args=[ast.Constant(value=condition), ast.Constant(value='False')],
            keywords=[]
        ))

        # If文の本体にデバッグ呼び出しを挿入
        new_body = [debug_condition_call, true_branch_debug] + node.body
        new_orelse = [false_branch_debug] + node.orelse if node.orelse else []

        # 新しいIfノードを作成
        new_if_node = ast.If(test=node.test, body=new_body, orelse=new_orelse)

        # 子ノードを再帰的に訪問
        self.generic_visit(new_if_node)
        return new_if_node


    def visit_Assign(self, node):
        if isinstance(node.targets[0], ast.Name):
            var_name = node.targets[0].id
            new_node = ast.Expr(
                ast.Call(
                    func=ast.Name(id='debug_variable', ctx=ast.Load()),
                    args=[
                        ast.Constant(value=var_name),
                        node.targets[0]
                    ],
                    keywords=[]
                )
            )
            return [node, new_node]
        return node

    def visit_Call(self, node):
        if isinstance(node.func, ast.Name) and node.func.id == 'print':
            return ast.Call(
                func=ast.Name(id='debug_print', ctx=ast.Load()),
                args=node.args,
                keywords=node.keywords
            )
        return node

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python debug_analizer.py <filename>")
        sys.exit(1)
    
    filename = sys.argv[1]
    visualizer.instrument_file(filename)
    visualizer.render('debug_flow')