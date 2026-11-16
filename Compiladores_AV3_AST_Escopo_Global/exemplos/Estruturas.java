public class Estruturas {
    public static int somar(int[] valores) {
        int total = 0;
        for (int valor : valores) {
            if (valor > 0) {
                total += valor;
            } else {
                continue;
            }
        }
        return total;
    }

    public static void main(String[] args) {
        int n = 0;
        for (int i = 0; i < 3; i++) {
            n = n + i;
        }
        while (n < 5) {
            n++;
        }
        do {
            n--;
        } while (n > 3);
        try {
            System.out.println(n);
        } catch (Exception erro) {
            System.out.println(erro);
        } finally {
            System.out.println("fim");
        }
    }
}
